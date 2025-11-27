"""
IFrame-Based Drag-and-Drop File Upload Widget for Jupyter

A standalone widget that enables drag-and-drop file uploads in JupyterLab
by using an iframe to bypass Lumino's event interception.

Files dropped in the iframe are read as base64 and sent to Python
via postMessage -> parent JavaScript -> hidden ipywidget.

Supported formats: CSV, Excel (XLSX, XLSM, XLS), Feather, Parquet
"""

import base64
import io
import logging
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, Javascript
from typing import Callable, Optional, Tuple, Dict

# Simple logger - set level to DEBUG to see messages
_logger = logging.getLogger(__name__)
def log(msg): _logger.debug(msg)


class IFrameDropWidget:
    """
    IFrame-based drag-and-drop widget for Jupyter notebooks.

    Creates an iframe with its own document context to bypass
    JupyterLab's Lumino event interception for drag-drop events.

    Usage:
        IFrameDropWidget.install_global_listener()

        def handle_data(filename, data):
            for sheet_name, df in data.items():
                print(f"Loaded {filename}[{sheet_name}]: {df.shape}")

        widget = IFrameDropWidget(on_data_ready=handle_data)
        widget.display()
        
        all_sheets = widget.data
        selected_df = widget.selected_dataframe
    """

    ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xlsm', '.xls', '.feather', '.parquet'}
    MAX_FILE_SIZE_MB = 50

    # Class-level counter for unique IDs and tracking if listener is installed
    _instance_counter = 0
    _global_listener_installed = False

    @classmethod
    def check_dependencies(cls) -> dict:
        """Check if optional dependencies are available.
        
        Returns a dict with dependency status:
        {
            'pandas': {'available': True, 'version': '2.0.0', 'required_for': 'all file types'},
            'openpyxl': {'available': True, 'version': '3.1.0', 'required_for': '.xlsx/.xlsm files'},
            ...
        }
        
        Usage:
            deps = IFrameDropWidget.check_dependencies()
            for name, info in deps.items():
                status = "OK" if info['available'] else "MISSING"
                print(f"{name}: {status} - needed for {info['required_for']}")
        """
        dependencies = {
            'pandas': {'module': 'pandas', 'required_for': 'all file types'},
            'openpyxl': {'module': 'openpyxl', 'required_for': '.xlsx/.xlsm files'},
            'xlrd': {'module': 'xlrd', 'required_for': '.xls files'},
            'pyarrow': {'module': 'pyarrow', 'required_for': '.feather/.parquet files'},
        }
        
        results = {}
        for name, info in dependencies.items():
            try:
                import importlib
                mod = importlib.import_module(info['module'])
                version = getattr(mod, '__version__', 'unknown')
                results[name] = {'available': True, 'version': version, 'required_for': info['required_for']}
            except ImportError:
                results[name] = {'available': False, 'version': None, 'required_for': info['required_for']}
        
        return results

    @classmethod
    def install_global_listener(cls):
        """
        Install the global postMessage listener once.

        IMPORTANT: Call this BEFORE creating any IFrameDropWidget instances,
        ideally at notebook startup when display() works reliably.
        """
        if cls._global_listener_installed:
            log('Global listener already installed')
            return

        js_code = '''
        (function() {
            if (window._iframeDropGlobalListener) {
                console.log('GLOBAL: Listener already exists');
                return;
            }

            window._iframeDropGlobalListener = function(event) {
                if (event.data && event.data.type === 'iframe_file_drop') {
                    const widgetId = event.data.widgetId;
                    console.log('GLOBAL: Received file for widget:', widgetId, 'file:', event.data.fileName);

                    const filenameInput = document.querySelector('.iframe-filename-' + widgetId + ' input');
                    const contentArea = document.querySelector('.iframe-content-' + widgetId + ' textarea');

                    console.log('GLOBAL: Found elements - input:', !!filenameInput, 'textarea:', !!contentArea);

                    if (filenameInput && contentArea) {
                        // Set content first
                        contentArea.value = event.data.fileContent;
                        contentArea.dispatchEvent(new Event('input', { bubbles: true }));

                        // Then filename (triggers Python callback)
                        setTimeout(function() {
                            filenameInput.value = event.data.fileName;
                            filenameInput.dispatchEvent(new Event('input', { bubbles: true }));
                            console.log('GLOBAL: Sent to Python widgets');
                        }, 50);
                    } else {
                        console.error('GLOBAL: Could not find widgets for', widgetId);
                        // Debug: list all elements with iframe- classes
                        const allIframeClasses = document.querySelectorAll('[class*="iframe-"]');
                        console.log('GLOBAL: Elements with iframe- classes:', allIframeClasses.length);
                        allIframeClasses.forEach(el => console.log('  -', el.className));
                    }
                }
            };

            window.addEventListener('message', window._iframeDropGlobalListener, false);
            console.log('GLOBAL: IFrame drop listener installed');
        })();
        '''

        display(Javascript(js_code))
        cls._global_listener_installed = True
        log('Global listener installation triggered')

    def __init__(self, on_dataframe_ready: Optional[Callable[[str, pd.DataFrame], None]] = None,
                 on_data_ready: Optional[Callable[[str, Dict[str, pd.DataFrame]], None]] = None):
        """
        Initialize the iframe drop widget.

        Args:
            on_dataframe_ready: DEPRECATED. Legacy callback for single DataFrame.
                               Signature: callback(filename: str, df: pd.DataFrame) -> None
            on_data_ready: New callback for full data dict.
                          Signature: callback(filename: str, data: Dict[str, pd.DataFrame]) -> None
        """
        self.on_dataframe_ready = on_dataframe_ready
        self.on_data_ready = on_data_ready

        # Use incrementing ID so we can track instances
        IFrameDropWidget._instance_counter += 1
        self._widget_id = f"iframe_drop_{IFrameDropWidget._instance_counter}"

        # Data storage
        self._data: Optional[Dict[str, pd.DataFrame]] = None
        self._selected_key: Optional[str] = None
        self._filename: Optional[str] = None

        self._create_widgets()
        self._setup_observers()

        log(f'IFrameDropWidget initialized with ID: {self._widget_id}')

    def _create_widgets(self):
        """Create all widget components."""
        # Hidden widgets for receiving data from iframe via parent JS
        self._file_name = widgets.Text(value='', description='')
        self._file_content = widgets.Textarea(value='', description='')
        self._file_name.layout.display = 'none'
        self._file_content.layout.display = 'none'

        # Give them identifiable IDs for global listener to find
        self._file_name.add_class(f'iframe-filename-{self._widget_id}')
        self._file_content.add_class(f'iframe-content-{self._widget_id}')

        # Status output for messages
        self.status_output = widgets.Output()

        # Dropdown selector for multi-sheet files
        self._selector = widgets.Dropdown(
            options=[],
            description='Select:',
            disabled=True,
            layout=widgets.Layout(display='none')
        )
        self._selector.observe(self._on_selection_change, names='value')

        # IFrame with embedded drop zone
        iframe_html = self._get_iframe_html()
        self.iframe_widget = widgets.HTML(value=iframe_html)

        # Main container (global listener handles all widgets)
        self.container = widgets.VBox([
            self.iframe_widget,
            self._selector,
            self.status_output,
            self._file_name,
            self._file_content,
        ])

    def _get_iframe_html(self) -> str:
        """Generate the iframe HTML with embedded drop zone."""
        # The srcdoc contains a complete HTML document with drop handling
        iframe_content = '''
<!DOCTYPE html>
<html>
<head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        #dropzone {
            width: 95%;
            height: 180px;
            border: 3px dashed #aaa;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        #dropzone.drag-over {
            border-color: #4CAF50;
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            transform: scale(1.02);
        }
        #dropzone.success {
            border-color: #4CAF50;
            border-style: solid;
            background: #e8f5e9;
        }
        #dropzone.error {
            border-color: #f44336;
            border-style: solid;
            background: #ffebee;
        }
        .icon { font-size: 48px; margin-bottom: 10px; }
        .title { color: #555; font-size: 18px; font-weight: bold; margin: 5px 0; }
        .subtitle { color: #888; font-size: 14px; }
        .info { color: #aaa; font-size: 12px; margin-top: 10px; }
        .status { color: #1976d2; font-size: 14px; font-weight: bold; }
        .status.success { color: #2e7d32; }
        .status.error { color: #c62828; }
    </style>
</head>
<body>
    <div id="dropzone">
        <div class="icon">📁</div>
        <div class="title">Drop data file here</div>
        <div class="subtitle">Drag and drop to load directly</div>
        <div class="info">CSV, Excel, Feather, Parquet (max 50MB)</div>
    </div>

    <script>
        const dropzone = document.getElementById('dropzone');
        const WIDGET_ID = '<!--WIDGET_ID-->';
        const MAX_SIZE_MB = 50;

        function showStatus(msg, type) {
            dropzone.className = type || '';
            dropzone.innerHTML = '<div class="status ' + (type || '') + '">' + msg + '</div>';
        }

        function resetDropzone() {
            dropzone.className = '';
            dropzone.innerHTML = `
                <div class="icon">📁</div>
                <div class="title">Drop data file here</div>
                <div class="subtitle">Drag and drop to load directly</div>
                <div class="info">CSV, Excel, Feather, Parquet (max 50MB)</div>
            `;
        }

        // Prevent defaults on all drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, e => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        // Visual feedback
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => {
                dropzone.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => {
                dropzone.classList.remove('drag-over');
            }, false);
        });

        // Handle drop
        dropzone.addEventListener('drop', function(e) {
            console.log('IFRAME: Drop event received!');

            const files = e.dataTransfer.files;
            if (files.length === 0) {
                showStatus('❌ No files detected', 'error');
                setTimeout(resetDropzone, 2000);
                return;
            }

            const file = files[0];
            const fileName = file.name;
            const fileNameLower = fileName.toLowerCase();
            console.log('IFRAME: File:', fileName, 'Size:', file.size);

            // Validate extension
            const validExt = ['.csv', '.xlsx', '.xlsm', '.xls', '.feather', '.parquet'];
            const hasValidExt = validExt.some(ext => fileNameLower.endsWith(ext));
            if (!hasValidExt) {
                showStatus('❌ Invalid file type. Use CSV, Excel, Feather, or Parquet', 'error');
                setTimeout(resetDropzone, 3000);
                return;
            }

            // Check size
            const sizeMB = file.size / (1024 * 1024);
            if (sizeMB > MAX_SIZE_MB) {
                showStatus('❌ File too large: ' + sizeMB.toFixed(1) + 'MB (max ' + MAX_SIZE_MB + 'MB)', 'error');
                setTimeout(resetDropzone, 3000);
                return;
            }

            showStatus('⏳ Reading: ' + fileName + '...', '');

            // Read file as base64
            const reader = new FileReader();

            reader.onload = function(event) {
                console.log('IFRAME: File read complete');
                showStatus('⏳ Sending to Python...', '');

                // Get base64 (remove data URL prefix)
                const base64 = event.target.result.split(',')[1];

                // Send to parent window
                window.parent.postMessage({
                    type: 'iframe_file_drop',
                    widgetId: WIDGET_ID,
                    fileName: fileName,
                    fileContent: base64
                }, '*');

                showStatus('✅ Sent: ' + fileName, 'success');
                setTimeout(resetDropzone, 3000);
            };

            reader.onerror = function() {
                showStatus('❌ Failed to read file', 'error');
                setTimeout(resetDropzone, 3000);
            };

            reader.readAsDataURL(file);
        }, false);

        console.log('IFRAME: Drop zone initialized for widget:', WIDGET_ID);
    </script>
</body>
</html>
        '''.replace('<!--WIDGET_ID-->', self._widget_id)

        # Escape for srcdoc attribute
        iframe_content_escaped = iframe_content.replace('"', '&quot;')

        return f'''
        <iframe
            id="{self._widget_id}"
            srcdoc="{iframe_content_escaped}"
            style="width: 100%; height: 220px; border: none; border-radius: 10px;"
            sandbox="allow-scripts"
        ></iframe>
        '''

    def _setup_observers(self):
        """Set up observers for receiving data from iframe."""
        self._file_name.observe(self._on_filename_change, names='value')

    def _on_selection_change(self, change):
        """Handle selection change in dropdown."""
        new_key = change.get('new')
        if new_key and self._data and new_key in self._data:
            self._selected_key = new_key
            df = self._data[new_key]
            self._show_success(f"{self._filename} [{new_key}]", df.shape)
            log(f'Selection changed to: {new_key}')

    def _on_filename_change(self, change):
        """Handle filename change (triggered when iframe sends file)."""
        filename = change.get('new', '')
        if not filename:
            return

        log(f'Received file from iframe: {filename}')

        content_b64 = self._file_content.value
        if not content_b64:
            self._show_error('No file content received')
            self._reset_inputs()
            return

        try:
            ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext not in self.ALLOWED_EXTENSIONS:
                self._show_error(f'Invalid file type: {ext}')
                self._reset_inputs()
                return

            content_bytes = base64.b64decode(content_b64)
            log(f'Decoded {len(content_bytes)} bytes')

            data = self._parse_file(filename, content_bytes)

            if data:
                self._data = data
                self._filename = filename
                
                keys = list(data.keys())
                self._selector.options = keys
                self._selector.value = keys[0]
                self._selected_key = keys[0]
                
                if len(keys) > 1:
                    self._selector.layout.display = 'block'
                    self._selector.disabled = False
                else:
                    self._selector.layout.display = 'none'
                
                first_df = data[keys[0]]
                self._show_success(f"{filename} [{keys[0]}]" if len(keys) > 1 else filename, first_df.shape)
                log(f'Data loaded: {len(data)} sheet(s)')

                if self.on_data_ready:
                    self.on_data_ready(filename, data)
                
                if self.on_dataframe_ready:
                    import warnings
                    warnings.warn(
                        "on_dataframe_ready is deprecated. Use on_data_ready for full dict access.",
                        DeprecationWarning,
                        stacklevel=2
                    )
                    self.on_dataframe_ready(filename, first_df)

        except Exception as e:
            log(f'Error processing file: {str(e)}')
            self._show_error(f'Error: {str(e)}')

        finally:
            self._reset_inputs()

    def _parse_file(self, filename: str, content: bytes) -> Dict[str, pd.DataFrame]:
        """Parse file content into dict of DataFrames.
        
        Raises ImportError with helpful message if required dependency is missing.
        """
        ext = '.' + filename.rsplit('.', 1)[-1].lower()
        
        if ext == '.csv':
            return {'data': pd.read_csv(io.BytesIO(content))}
        
        elif ext in ('.xlsx', '.xlsm'):
            try:
                import openpyxl  # noqa: F401
            except ImportError:
                raise ImportError(
                    f"Cannot read {ext} file: 'openpyxl' is not installed.\n\n"
                    "Install it in this Jupyter kernel's environment:\n"
                    "  !pip install openpyxl\n\n"
                    "Then restart the kernel."
                )
            excel_file = pd.ExcelFile(io.BytesIO(content), engine='openpyxl')
            return {sheet: pd.read_excel(excel_file, sheet_name=sheet) 
                    for sheet in excel_file.sheet_names}
        
        elif ext == '.xls':
            try:
                import xlrd  # noqa: F401
            except ImportError:
                raise ImportError(
                    "Cannot read .xls file: 'xlrd' is not installed.\n\n"
                    "Install it in this Jupyter kernel's environment:\n"
                    "  !pip install xlrd\n\n"
                    "Then restart the kernel."
                )
            excel_file = pd.ExcelFile(io.BytesIO(content), engine='xlrd')
            return {sheet: pd.read_excel(excel_file, sheet_name=sheet) 
                    for sheet in excel_file.sheet_names}
        
        elif ext == '.feather':
            try:
                import pyarrow  # noqa: F401
            except ImportError:
                raise ImportError(
                    "Cannot read .feather file: 'pyarrow' is not installed.\n\n"
                    "Install it in this Jupyter kernel's environment:\n"
                    "  !pip install pyarrow\n\n"
                    "Then restart the kernel."
                )
            return {'data': pd.read_feather(io.BytesIO(content))}
        
        elif ext == '.parquet':
            try:
                import pyarrow  # noqa: F401
            except ImportError:
                raise ImportError(
                    "Cannot read .parquet file: 'pyarrow' is not installed.\n\n"
                    "Install it in this Jupyter kernel's environment:\n"
                    "  !pip install pyarrow\n\n"
                    "Then restart the kernel."
                )
            return {'data': pd.read_parquet(io.BytesIO(content))}
        
        else:
            raise ValueError(f'Unsupported extension: {ext}')

    def _reset_inputs(self):
        """Reset hidden inputs for next file."""
        self._file_name.value = ''
        self._file_content.value = ''

    def _show_success(self, filename: str, shape: Tuple[int, int]):
        """Display success message."""
        with self.status_output:
            self.status_output.clear_output(wait=True)
            display(widgets.HTML(f'''
            <div style="color: #2e7d32; padding: 15px; margin: 10px 0;
                        background: #e8f5e9; border-radius: 5px; text-align: center;
                        border: 1px solid #a5d6a7;">
                <strong>✓ Loaded:</strong> {filename}<br>
                <span style="font-size: 12px; color: #666;">{shape[0]} rows × {shape[1]} columns</span>
            </div>
            '''))

    def _show_error(self, message: str):
        """Display error message."""
        with self.status_output:
            self.status_output.clear_output(wait=True)
            display(widgets.HTML(f'''
            <div style="color: #c62828; padding: 15px; margin: 10px 0;
                        background: #ffebee; border-radius: 5px; text-align: center;
                        border: 1px solid #ef9a9a;">
                <strong>✗ Error:</strong> {message}
            </div>
            '''))

    def clear_status(self):
        """Clear status message."""
        with self.status_output:
            self.status_output.clear_output()

    @property
    def widget(self):
        """Return the container widget for embedding."""
        return self.container

    @property
    def data(self) -> Optional[Dict[str, pd.DataFrame]]:
        """Return all loaded DataFrames as dict."""
        return self._data

    @property
    def selected_dataframe(self) -> Optional[pd.DataFrame]:
        """Return currently selected DataFrame."""
        if self._data and self._selected_key:
            return self._data.get(self._selected_key)
        return None

    @property
    def selected_key(self) -> Optional[str]:
        """Return key of currently selected DataFrame."""
        return self._selected_key

    @property
    def sheet_names(self) -> list:
        """Return list of available sheet/data names."""
        return list(self._data.keys()) if self._data else []

    def display(self):
        """Display the widget."""
        display(self.container)
