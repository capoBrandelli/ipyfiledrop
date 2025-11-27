"""
IFrame-Based Drag-and-Drop File Upload Widget for Jupyter

A standalone widget that enables drag-and-drop file uploads in JupyterLab
by using an iframe to bypass Lumino's event interception.

Files dropped in the iframe are read as base64 and sent to Python
via postMessage -> parent JavaScript -> hidden ipywidget.

Supported formats: CSV, Excel (XLSX, XLSM, XLS), Feather, Parquet, ZIP, TAR.GZ
"""

import base64
import io
import logging
import zipfile
import tarfile
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
            for key, df in data.items():
                print(f"Loaded {filename}[{key}]: {df.shape}")

        # Single file mode (default) - each drop replaces previous data
        widget = IFrameDropWidget(on_data_ready=handle_data)
        
        # Multi-file mode - files accumulate, Clear button shown
        widget = IFrameDropWidget(on_data_ready=handle_data, retain_data=True)
        
        widget.display()
        
        all_data = widget.data
        selected_df = widget.selected_dataframe
    """

    ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xlsm', '.xls', '.feather', '.parquet'}
    ARCHIVE_EXTENSIONS = {'.zip', '.tar.gz', '.tgz'}
    MAX_FILE_SIZE_MB = 200
    MAX_FILES = 1000
    MAX_FILES_PER_DROP = 50  # Max files in single drop operation
    RAM_WARNING_THRESHOLD_MB = 500

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
        """
        dependencies = {
            'pandas': {'module': 'pandas', 'required_for': 'all file types'},
            'openpyxl': {'module': 'openpyxl', 'required_for': '.xlsx/.xlsm files'},
            'xlrd': {'module': 'xlrd', 'required_for': '.xls files'},
            'pyarrow': {'module': 'pyarrow', 'required_for': '.feather/.parquet files'},
            'psutil': {'module': 'psutil', 'required_for': 'RAM usage warnings (optional)'},
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

    def __init__(self, 
                 on_dataframe_ready: Optional[Callable[[str, pd.DataFrame], None]] = None,
                 on_data_ready: Optional[Callable[[str, Dict[str, pd.DataFrame]], None]] = None,
                 retain_data: bool = False):
        """
        Initialize the iframe drop widget.

        Args:
            on_dataframe_ready: DEPRECATED. Legacy callback for single DataFrame.
                               Signature: callback(filename: str, df: pd.DataFrame) -> None
            on_data_ready: New callback for full data dict.
                          Signature: callback(filename: str, data: Dict[str, pd.DataFrame]) -> None
            retain_data: If True, accumulate dropped files (show Clear button).
                        If False (default), replace data on each drop.
        """
        self.on_dataframe_ready = on_dataframe_ready
        self.on_data_ready = on_data_ready
        self.retain_data = retain_data

        # Use incrementing ID so we can track instances
        IFrameDropWidget._instance_counter += 1
        self._widget_id = f"iframe_drop_{IFrameDropWidget._instance_counter}"

        # Data storage - dict that can accumulate when retain_data=True
        self._data: Dict[str, pd.DataFrame] = {}
        self._selected_key: Optional[str] = None
        self._current_filename: Optional[str] = None
        self._failed_imports: list = []  # List of {'filename': str, 'error': str}

        self._create_widgets()
        self._setup_observers()

        log(f'IFrameDropWidget initialized with ID: {self._widget_id}, retain_data={retain_data}')

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

        # Dropdown selector for accumulated files
        self._selector = widgets.Dropdown(
            options=[],
            description='Select:',
            disabled=True,
            layout=widgets.Layout(display='none', width='auto', min_width='200px')
        )
        self._selector.observe(self._on_selection_change, names='value')

        # Clear button - only shown when retain_data=True and data exists
        self._clear_button = widgets.Button(
            description='Clear All',
            icon='trash',
            button_style='warning',
            layout=widgets.Layout(display='none', width='100px')
        )
        self._clear_button.on_click(self._on_clear_click)

        # File count label
        self._file_count_label = widgets.HTML(
            value='',
            layout=widgets.Layout(display='none', margin='0 10px')
        )

        # Control row: selector + file count + clear button
        self._control_row = widgets.HBox([
            self._selector,
            self._file_count_label,
            self._clear_button
        ], layout=widgets.Layout(display='none', align_items='center'))

        # IFrame with embedded drop zone
        iframe_html = self._get_iframe_html()
        self.iframe_widget = widgets.HTML(value=iframe_html)

        # Main container (global listener handles all widgets)
        self.container = widgets.VBox([
            self.iframe_widget,
            self._control_row,
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
        <div class="info">Drop files here (max 200MB each, 50 files)</div>
    </div>

    <script>
        const dropzone = document.getElementById('dropzone');
        const WIDGET_ID = '<!--WIDGET_ID-->';
        const MAX_SIZE_MB = 200;
        const MAX_FILES_PER_DROP = 50;

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
                <div class="info">Drop files here (max 200MB each, 50 files)</div>
            `;
        }

        function readFileAsBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = function(event) {
                    const base64 = event.target.result.split(',')[1];
                    resolve(base64);
                };
                reader.onerror = function() {
                    reject(new Error('Failed to read file'));
                };
                reader.readAsDataURL(file);
            });
        }

        function delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
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

        // Handle drop - multi-file support
        dropzone.addEventListener('drop', async function(e) {
            console.log('IFRAME: Drop event received!');

            const files = Array.from(e.dataTransfer.files);
            if (files.length === 0) {
                showStatus('❌ No files detected', 'error');
                setTimeout(resetDropzone, 2000);
                return;
            }

            if (files.length > MAX_FILES_PER_DROP) {
                showStatus('❌ Too many files: ' + files.length + ' (max ' + MAX_FILES_PER_DROP + ')', 'error');
                setTimeout(resetDropzone, 3000);
                return;
            }

            const validExt = ['.csv', '.xlsx', '.xlsm', '.xls', '.feather', '.parquet', '.zip', '.tar.gz', '.tgz'];
            const validFiles = [];
            const errors = [];
            
            for (const file of files) {
                const fileName = file.name;
                const fileNameLower = fileName.toLowerCase();
                const sizeMB = file.size / (1024 * 1024);
                
                const hasValidExt = validExt.some(ext => fileNameLower.endsWith(ext));
                if (!hasValidExt) {
                    errors.push(fileName + ': invalid type');
                    continue;
                }
                
                if (sizeMB > MAX_SIZE_MB) {
                    errors.push(fileName + ': too large (' + sizeMB.toFixed(1) + 'MB)');
                    continue;
                }
                
                validFiles.push(file);
            }

            if (errors.length > 0 && validFiles.length === 0) {
                showStatus('❌ ' + errors.join(', '), 'error');
                setTimeout(resetDropzone, 3000);
                return;
            }

            const totalFiles = validFiles.length;
            let processed = 0;
            let failed = 0;

            for (const file of validFiles) {
                processed++;
                const progress = totalFiles > 1 ? ' (' + processed + '/' + totalFiles + ')' : '';
                showStatus('⏳ Reading: ' + file.name + progress, '');

                try {
                    const base64 = await readFileAsBase64(file);
                    showStatus('⏳ Sending: ' + file.name + progress, '');
                    
                    window.parent.postMessage({
                        type: 'iframe_file_drop',
                        widgetId: WIDGET_ID,
                        fileName: file.name,
                        fileContent: base64
                    }, '*');

                    if (processed < totalFiles) {
                        await delay(100);
                    }
                } catch (err) {
                    console.error('IFRAME: Failed to read', file.name, err);
                    failed++;
                }
            }

            if (failed > 0) {
                showStatus('⚠️ Sent ' + (processed - failed) + '/' + totalFiles + ' files (' + failed + ' failed)', 'error');
            } else if (errors.length > 0) {
                showStatus('⚠️ Sent ' + totalFiles + ' files, skipped ' + errors.length + ' invalid', 'success');
            } else {
                showStatus('✅ Sent ' + totalFiles + ' file' + (totalFiles > 1 ? 's' : ''), 'success');
            }
            
            setTimeout(resetDropzone, 3000);
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
            self._show_success(f"Selected: {new_key}", df.shape)
            log(f'Selection changed to: {new_key}')

    def _on_clear_click(self, button):
        """Handle Clear button click - reset all accumulated data."""
        self.clear_data()

    def clear_data(self):
        """
        Clear all accumulated data and reset widget to initial state.
        
        This removes all loaded DataFrames, clears failed imports,
        and hides the selector/clear button.
        """
        self._data = {}
        self._selected_key = None
        self._current_filename = None
        self._failed_imports = []
        
        # Reset UI
        self._selector.options = []
        self._selector.disabled = True
        self._control_row.layout.display = 'none'
        
        # Clear status
        self.clear_status()
        
        log('Data cleared')

    def _update_file_count(self):
        """Update the file count label."""
        count = len(self._data)
        failed = len(self._failed_imports)
        
        text = f"<span style='color: #666; font-size: 12px;'>{count} file(s) loaded</span>"
        if failed > 0:
            text += f"<span style='color: #c62828; font-size: 12px; margin-left: 10px;'>{failed} failed</span>"
        
        self._file_count_label.value = text
        self._file_count_label.layout.display = 'block'

    def _check_ram_warning(self):
        """Check available RAM and log warning if low."""
        try:
            import psutil
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            if available_mb < self.RAM_WARNING_THRESHOLD_MB:
                log(f'WARNING: Low RAM available: {available_mb:.0f}MB')
                with self.status_output:
                    display(widgets.HTML(f'''
                    <div style="color: #f57c00; padding: 5px; font-size: 12px;">
                        ⚠️ Low memory: {available_mb:.0f}MB available
                    </div>
                    '''))
        except ImportError:
            # psutil not installed, skip RAM check
            pass
        except Exception as e:
            log(f'RAM check failed: {e}')

    def _get_extension(self, filename: str) -> str:
        """Get file extension, handling compound extensions like .tar.gz."""
        lower = filename.lower()
        if lower.endswith('.tar.gz'):
            return '.tar.gz'
        return '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

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
            ext = self._get_extension(filename)
            all_allowed = self.ALLOWED_EXTENSIONS | self.ARCHIVE_EXTENSIONS
            if ext not in all_allowed:
                self._show_error(f'Invalid file type: {ext}')
                self._reset_inputs()
                return

            content_bytes = base64.b64decode(content_b64)
            log(f'Decoded {len(content_bytes)} bytes')

            # Check RAM before parsing
            self._check_ram_warning()

            # Parse file (handles both single files and archives)
            new_data = self._parse_file(filename, content_bytes)

            if new_data:
                # Prepare final keys for the data
                final_data = {}
                is_archive = ext in self.ARCHIVE_EXTENSIONS
                
                for key, df in new_data.items():
                    if is_archive:
                        # Archive: use path from archive as key
                        final_key = key
                    else:
                        # Single file
                        if len(new_data) == 1 and key == 'data':
                            # Simple file (CSV, Feather, Parquet): use filename
                            final_key = filename
                        else:
                            # Multi-sheet Excel: filename/SheetName
                            final_key = f"{filename}/{key}"
                    final_data[final_key] = df

                if self.retain_data:
                    # ACCUMULATE mode: check limits and merge
                    total_after = len(self._data) + len(final_data)
                    if total_after > self.MAX_FILES:
                        self._show_error(
                            f'File limit exceeded. Max {self.MAX_FILES} files allowed. '
                            f'Currently have {len(self._data)}, trying to add {len(final_data)}.'
                        )
                        self._reset_inputs()
                        return

                    # Check for overwrites
                    overwrites = [k for k in final_data.keys() if k in self._data]
                    
                    # Merge data
                    self._data.update(final_data)
                    
                    # Show controls
                    self._control_row.layout.display = 'flex'
                    self._selector.layout.display = 'block'
                    self._clear_button.layout.display = 'block'
                    self._update_file_count()
                    
                    # Show appropriate message
                    first_key = list(final_data.keys())[0]
                    first_df = final_data[first_key]
                    
                    if overwrites:
                        self._show_warning(
                            f"Added {len(final_data)} file(s). Overwrote: {', '.join(overwrites[:3])}"
                            f"{'...' if len(overwrites) > 3 else ''}",
                            first_df.shape
                        )
                    else:
                        self._show_success(
                            f"Added {len(final_data)} file(s). Total: {len(self._data)}",
                            first_df.shape
                        )
                else:
                    # REPLACE mode: clear and set new data
                    self._data = final_data
                    
                    # Show selector only if multiple keys
                    if len(final_data) > 1:
                        self._control_row.layout.display = 'flex'
                        self._selector.layout.display = 'block'
                        self._selector.disabled = False
                        # Hide clear button and file count in replace mode
                        self._clear_button.layout.display = 'none'
                        self._file_count_label.layout.display = 'none'
                    else:
                        self._control_row.layout.display = 'none'
                    
                    first_key = list(final_data.keys())[0]
                    first_df = final_data[first_key]
                    display_name = f"{filename} [{first_key}]" if len(final_data) > 1 else filename
                    self._show_success(display_name, first_df.shape)

                # Update selector options and selection
                self._current_filename = filename
                keys = list(self._data.keys())
                self._selector.options = keys
                
                # Select the first key from newly added data
                first_new_key = list(final_data.keys())[0]
                self._selector.value = first_new_key
                self._selected_key = first_new_key
                self._selector.disabled = False

                log(f'Data {"accumulated" if self.retain_data else "replaced"}: {len(final_data)} new, {len(self._data)} total')

                # Callbacks
                if self.on_data_ready:
                    self.on_data_ready(filename, final_data)

                if self.on_dataframe_ready:
                    import warnings
                    warnings.warn(
                        "on_dataframe_ready is deprecated. Use on_data_ready for full dict access.",
                        DeprecationWarning,
                        stacklevel=2
                    )
                    self.on_dataframe_ready(filename, final_data[first_new_key])

        except Exception as e:
            log(f'Error processing file: {str(e)}')
            self._show_error(f'Error: {str(e)}')

        finally:
            self._reset_inputs()

    def _parse_file(self, filename: str, content: bytes) -> Dict[str, pd.DataFrame]:
        """
        Parse file content into dict of DataFrames.
        
        Handles both regular files and archives. For archives, extracts
        and parses all supported files within.
        """
        ext = self._get_extension(filename)
        
        if ext in self.ARCHIVE_EXTENSIONS:
            return self._parse_archive(filename, content)
        else:
            return self._parse_single_file(filename, content)

    def _parse_archive(self, archive_name: str, content: bytes) -> Dict[str, pd.DataFrame]:
        """
        Extract and parse supported files from an archive.
        
        Extracts ZIP, TAR.GZ, and TGZ archives in-memory (no temp files).
        Files that fail to parse are added to self._failed_imports.
        """
        ext = self._get_extension(archive_name)
        
        if ext == '.zip':
            return self._parse_zip(archive_name, content)
        elif ext in ('.tar.gz', '.tgz'):
            return self._parse_tarball(archive_name, content)
        else:
            raise ValueError(f'Unsupported archive format: {archive_name}')

    def _parse_zip(self, archive_name: str, content: bytes) -> Dict[str, pd.DataFrame]:
        """Parse a ZIP archive in-memory."""
        results = {}
        
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            for zip_info in zf.infolist():
                # Skip directories
                if zip_info.is_dir():
                    continue
                
                inner_filename = zip_info.filename
                inner_ext = self._get_extension(inner_filename)
                
                # Skip unsupported files
                if inner_ext not in self.ALLOWED_EXTENSIONS:
                    continue
                
                try:
                    file_content = zf.read(inner_filename)
                    parsed = self._parse_single_file(inner_filename, file_content)
                    
                    # For single-result files, use the path as key
                    # For multi-sheet Excel, prefix each sheet with path
                    if len(parsed) == 1 and 'data' in parsed:
                        results[inner_filename] = parsed['data']
                    else:
                        for sheet_name, df in parsed.items():
                            results[f"{inner_filename}/{sheet_name}"] = df
                            
                except Exception as e:
                    self._failed_imports.append({
                        'filename': f"{archive_name}:{inner_filename}",
                        'error': str(e)
                    })
                    log(f'Failed to parse {inner_filename} from {archive_name}: {e}')
                    continue
        
        return results

    def _parse_tarball(self, archive_name: str, content: bytes) -> Dict[str, pd.DataFrame]:
        """Parse a TAR.GZ/TGZ archive in-memory."""
        results = {}
        
        with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as tf:
            for member in tf.getmembers():
                # Skip directories
                if not member.isfile():
                    continue
                
                inner_filename = member.name
                inner_ext = self._get_extension(inner_filename)
                
                # Skip unsupported files
                if inner_ext not in self.ALLOWED_EXTENSIONS:
                    continue
                
                try:
                    file_obj = tf.extractfile(member)
                    if file_obj is None:
                        continue
                    file_content = file_obj.read()
                    parsed = self._parse_single_file(inner_filename, file_content)
                    
                    if len(parsed) == 1 and 'data' in parsed:
                        results[inner_filename] = parsed['data']
                    else:
                        for sheet_name, df in parsed.items():
                            results[f"{inner_filename}/{sheet_name}"] = df
                            
                except Exception as e:
                    self._failed_imports.append({
                        'filename': f"{archive_name}:{inner_filename}",
                        'error': str(e)
                    })
                    log(f'Failed to parse {inner_filename} from {archive_name}: {e}')
                    continue
        
        return results

    def _parse_single_file(self, filename: str, content: bytes) -> Dict[str, pd.DataFrame]:
        """Parse a single file into dict of DataFrames.
        
        Raises ImportError with helpful message if required dependency is missing.
        """
        ext = self._get_extension(filename)
        
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

    def _show_success(self, message: str, shape: Tuple[int, int]):
        """Display success message."""
        with self.status_output:
            self.status_output.clear_output(wait=True)
            display(widgets.HTML(f'''
            <div style="color: #2e7d32; padding: 15px; margin: 10px 0;
                        background: #e8f5e9; border-radius: 5px; text-align: center;
                        border: 1px solid #a5d6a7;">
                <strong>✓ {message}</strong><br>
                <span style="font-size: 12px; color: #666;">{shape[0]} rows × {shape[1]} columns</span>
            </div>
            '''))

    def _show_warning(self, message: str, shape: Tuple[int, int]):
        """Display warning message with DataFrame info."""
        with self.status_output:
            self.status_output.clear_output(wait=True)
            display(widgets.HTML(f'''
            <div style="color: #f57c00; padding: 15px; margin: 10px 0;
                        background: #fff3e0; border-radius: 5px; text-align: center;
                        border: 1px solid #ffcc80;">
                <strong>⚠ {message}</strong><br>
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
    def data(self) -> Dict[str, pd.DataFrame]:
        """
        Return all loaded DataFrames as dict.
        
        Keys are:
        - For single files: filename (e.g., 'myfile.csv')
        - For multi-sheet Excel: 'filename.xlsx/SheetName'
        - For archive contents: 'path/inside/archive/file.csv'
        
        Returns empty dict if no data loaded.
        """
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
    def keys(self) -> list:
        """Return list of all loaded data keys."""
        return list(self._data.keys())

    @property
    def sheet_names(self) -> list:
        """Return list of available sheet/data names. Alias for keys property."""
        return self.keys

    @property
    def failed_imports(self) -> list:
        """
        Return list of files that failed to import.
        
        Returns:
            List of dicts: [{'filename': str, 'error': str}, ...]
        """
        return self._failed_imports.copy()

    def display(self):
        """Display the widget."""
        display(self.container)
