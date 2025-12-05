"""
FileDrop - Compact multi-file drop widget for Jupyter notebooks.

Provides a high-level API for multiple drop zones with automatic
global listener installation and DataFrame access.

Includes data import pipeline for:
- Core data extraction from messy files
- Data cleaning and normalization
- Combining multiple DataFrames
"""

import logging
from typing import Callable, Dict, Optional, List, Union
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from .iframe_drop_widget import IFrameDropWidget
from .pipeline import (
    ExtractedData,
    extract_core_data,
    clean_dataframe,
    combine_dataframes,
    apply_cleaners,
    CLEANING_PRESETS,
)

logger = logging.getLogger(__name__)

# Type alias for cleaner functions
CleanerFunc = Callable[[pd.DataFrame, Optional[str]], pd.DataFrame]


class FileDrop:
    """
    Compact multi-file drop widget manager.

    Creates multiple drop zones with automatic global listener installation.
    Files are automatically parsed to pandas DataFrames.
    
    Supports:
    - Multiple sequential file drops (with retain_data=True)
    - Archive extraction (.zip, .tar.gz, .tgz)
    - CSV, Excel, Feather, Parquet files
    - Up to 1000 files total, 200MB per drop

    Example:
        # Basic usage - each drop replaces previous data
        fd = FileDrop("Train", "Test").display()
        df_train = fd["Train"]  # Returns selected DataFrame or None
        
        # Multi-file mode - files accumulate
        fd = FileDrop("Data", retain_data=True).display()
        # Drop file1.csv, then file2.csv - both are kept
        all_data = fd.get_all_data("Data")  # Dict of all DataFrames
        fd.clear("Data")  # Clear and start fresh
        
        # Check for failed imports (from archives)
        failed = fd.get_failed_imports("Data")
    """

    def __init__(self, 
                 *labels, 
                 retain_data: bool = False,
                 extract_core: bool = False,
                 clean: str = None,
                 cleaner: CleanerFunc = None,
                 cleaners: List[CleanerFunc] = None):
        """
        Initialize FileDrop with named drop zones.

        Args:
            *labels: Variable number of drop zone labels (e.g., "Train", "Test")
            retain_data: If True, accumulate files in each zone (show Clear button).
                        If False (default), each drop replaces previous data.
            extract_core: If True, automatically extract core data from messy files
                         using density analysis and header detection.
            clean: Cleaning preset name ('none', 'minimal', 'standard', 'aggressive').
                  See CLEANING_PRESETS for details.
            cleaner: Custom cleaner function: (df, filename) -> df
            cleaners: List of cleaner functions to apply in sequence
        """
        # Auto-install global listener (safe if already installed)
        IFrameDropWidget.install_global_listener()

        self._retain_data = retain_data
        self._extract_core = extract_core
        self._clean_preset = clean
        self._cleaner = cleaner
        self._cleaners = cleaners
        
        self._widgets = {}      # label -> IFrameDropWidget
        self._datasets = {}     # label -> {'filename': str, 'data': Dict[str, DataFrame], 'selected': str}
        self._labels = []       # Ordered list of labels
        self._container = widgets.VBox()  # Main container for embedding
        self._extracted = {}    # label -> {key: ExtractedData} (when extract_core=True)

        # Create initial widgets
        for label in labels:
            self._add_widget(label)

        # Build initial UI
        self._update_ui()

    def _add_widget(self, label):
        """Create IFrameDropWidget for a label with callback."""
        def on_data_ready(filename, data):
            # Apply pipeline processing to each DataFrame
            processed_data = {}
            extracted_results = {}
            
            for key, df in data.items():
                # Step 1: Extract core if enabled
                if self._extract_core:
                    try:
                        extracted = extract_core_data(df)
                        extracted_results[key] = extracted
                        df = extracted.core
                        logger.debug(f"FileDrop: Extracted core from '{key}': {df.shape}, confidence={extracted.confidence:.2f}")
                    except Exception as e:
                        logger.warning(f"FileDrop: Core extraction failed for '{key}': {e}")
                
                # Step 2: Apply cleaning
                try:
                    if self._cleaners:
                        df = apply_cleaners(df, self._cleaners, filename)
                    elif self._cleaner:
                        df = self._cleaner(df, filename)
                    elif self._clean_preset and self._clean_preset != 'none':
                        df = clean_dataframe(df, preset=self._clean_preset, filename=filename)
                except Exception as e:
                    logger.warning(f"FileDrop: Cleaning failed for '{key}': {e}")
                
                processed_data[key] = df
            
            # Store extracted results for later access
            if self._extract_core and extracted_results:
                if label not in self._extracted:
                    self._extracted[label] = {}
                self._extracted[label].update(extracted_results)
            
            # Update widget's data with processed DataFrames
            widget = self._widgets[label]
            for key, df in processed_data.items():
                widget._data[key] = df
            
            # Update selector options if needed
            if len(widget._data) > 1:
                widget._selector.options = list(widget._data.keys())
                if widget._selector.value not in widget._data:
                    widget._selector.value = list(widget._data.keys())[0]
            
            # Update datasets tracking
            self._datasets[label] = {
                'filename': filename,
                'data': widget._data,
                'selected': widget.selected_key
            }
            logger.debug(f"FileDrop: Loaded '{filename}' into '{label}' ({len(data)} new, {len(widget._data)} total)")

        widget = IFrameDropWidget(on_data_ready=on_data_ready, retain_data=self._retain_data)
        self._widgets[label] = widget
        self._labels.append(label)

    def _build_ui(self):
        """Build and return the widget hierarchy."""
        if not self._widgets:
            return widgets.HTML("<p>No drop zones</p>")

        # Create VBox for each label with header
        boxes = []
        for label in self._labels:
            if label in self._widgets:
                header = widgets.HTML(f"<h4 style='margin:0 0 5px 0'>{label}</h4>")
                box = widgets.VBox([header, self._widgets[label].widget])
                boxes.append(box)

        return widgets.HBox(boxes)

    def _update_ui(self):
        """Update the container's children."""
        self._container.children = [self._build_ui()]

    @property
    def ui(self):
        """
        Return the widget for embedding in containers.

        Use this property when embedding FileDrop in ipywidgets containers
        like Accordion, Tab, VBox, etc.

        Example:
            fd = FileDrop("Train", "Test")
            accordion = widgets.Accordion(children=[fd.ui])
            display(accordion)

        Returns:
            widgets.VBox: The embeddable widget container
        """
        return self._container

    def display(self):
        """
        Display the widget and return self for chaining.

        Returns:
            FileDrop: self for method chaining
        """
        display(self._container)
        return self

    def add(self, label):
        """
        Add a new drop zone.

        Args:
            label: Name for the new drop zone

        Returns:
            FileDrop: self for method chaining
        """
        if label in self._widgets:
            logger.warning(f"FileDrop: Label '{label}' already exists")
            return self

        self._add_widget(label)
        self._update_ui()
        return self

    def remove(self, label):
        """
        Remove a drop zone and clear its data.

        Args:
            label: Name of the drop zone to remove

        Returns:
            FileDrop: self for method chaining
        """
        if label not in self._widgets:
            logger.warning(f"FileDrop: Label '{label}' not found")
            return self

        del self._widgets[label]
        self._datasets.pop(label, None)
        self._labels.remove(label)
        self._update_ui()
        return self

    def clear(self, label: str) -> 'FileDrop':
        """
        Clear all data for a specific drop zone.
        
        Args:
            label: Name of the drop zone to clear
            
        Returns:
            FileDrop: self for method chaining
            
        Raises:
            KeyError: If label doesn't exist
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        
        self._widgets[label].clear_data()
        self._datasets.pop(label, None)
        return self

    def __getitem__(self, label):
        """
        Get selected DataFrame by label.

        Args:
            label: Drop zone label

        Returns:
            pandas.DataFrame or None if no file loaded

        Raises:
            KeyError: If label doesn't exist
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        # Read directly from widget to reflect dropdown selection
        return self._widgets[label].selected_dataframe

    def get_all_data(self, label: str) -> Dict[str, pd.DataFrame]:
        """
        Get all accumulated DataFrames for a label.
        
        Args:
            label: Drop zone label
            
        Returns:
            Dict[str, DataFrame] - all accumulated data (empty dict if none)
            
        Raises:
            KeyError: If label doesn't exist
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        return self._widgets[label].data

    def get_all_sheets(self, label) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Get all DataFrames for a label. Alias for get_all_data().

        Args:
            label: Drop zone label

        Returns:
            Dict[str, DataFrame] or empty dict if no file loaded

        Raises:
            KeyError: If label doesn't exist
        """
        return self.get_all_data(label)

    def get_failed_imports(self, label: str) -> List[dict]:
        """
        Get list of failed imports for a label.
        
        Args:
            label: Drop zone label
            
        Returns:
            List of dicts: [{'filename': str, 'error': str}, ...]
            
        Raises:
            KeyError: If label doesn't exist
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        return self._widgets[label].failed_imports

    def select_sheet(self, label: str, sheet_name: str) -> 'FileDrop':
        """
        Select a specific sheet/file for a label.

        Args:
            label: Drop zone label
            sheet_name: Name of sheet/file to select

        Returns:
            FileDrop: self for method chaining

        Raises:
            KeyError: If label doesn't exist
            ValueError: If no data loaded or sheet not found
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        
        widget_data = self._widgets[label].data
        if not widget_data:
            raise ValueError(f"No data loaded for '{label}'")
        if sheet_name not in widget_data:
            raise ValueError(f"Key '{sheet_name}' not found. Available: {list(widget_data.keys())}")
        
        self._widgets[label]._selector.value = sheet_name
        return self

    @property
    def datasets(self):
        """
        Get all loaded datasets.

        Returns:
            dict: {label: {'filename': str, 'data': Dict[str, DataFrame], 'selected': str}} for loaded files
        """
        result = {}
        for label in self._labels:
            if label in self._widgets:
                widget = self._widgets[label]
                if widget.data:
                    result[label] = {
                        'filename': widget._current_filename,
                        'data': {k: v.copy() for k, v in widget.data.items()},
                        'selected': widget.selected_key
                    }
        return result

    @property
    def retain_data(self) -> bool:
        """Return whether retain_data mode is enabled."""
        return self._retain_data

    def extract(self, label: str, key: str = None) -> Union[ExtractedData, Dict[str, ExtractedData]]:
        """
        Get extraction results for a label.
        
        Requires extract_core=True when creating the FileDrop.
        
        Args:
            label: Drop zone label
            key: Optional specific key; if None, returns single result or dict
            
        Returns:
            Single ExtractedData if key provided or only one result,
            else dict of all results
            
        Raises:
            KeyError: If label or key doesn't exist
            ValueError: If extract_core not enabled or no data
            
        Example:
            fd = FileDrop("Data", extract_core=True)
            # ... drop file ...
            result = fd.extract("Data")
            result.core  # Cleaned DataFrame
            result.metadata  # {'Report Date': '2024-01-15', ...}
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        if not self._extract_core:
            raise ValueError("extract_core not enabled. Create FileDrop with extract_core=True")
        if label not in self._extracted or not self._extracted[label]:
            raise ValueError(f"No extracted data for '{label}'")
        
        if key is not None:
            if key not in self._extracted[label]:
                raise KeyError(f"Key '{key}' not found in '{label}'")
            return self._extracted[label][key]
        
        # Return single result if only one, else dict
        results = self._extracted[label]
        if len(results) == 1:
            return list(results.values())[0]
        return results

    def combine(self, 
                label: str,
                combiner: Callable[[Dict[str, pd.DataFrame]], pd.DataFrame] = None,
                add_source: bool = False,
                ignore_index: bool = True,
                include_metadata: List[str] = None) -> pd.DataFrame:
        """
        Combine all DataFrames for a label into one.
        
        Args:
            label: Drop zone label
            combiner: Custom combiner function: (data_dict) -> DataFrame
            add_source: Add '_source' column with original key
            ignore_index: Reset index after concat
            include_metadata: Metadata keys to add as columns (requires extract_core=True)
            
        Returns:
            Combined DataFrame
            
        Raises:
            KeyError: If label doesn't exist
            ValueError: If no data or include_metadata without extract_core
            
        Example:
            df = fd.combine("Data", add_source=True)
            df = fd.combine("Data", include_metadata=["date", "author"])
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        
        data = self._widgets[label].data
        if not data:
            raise ValueError(f"No data for '{label}'")
        
        # Use custom combiner if provided
        if combiner is not None:
            return combiner(data)
        
        # Get metadata if requested
        metadata = None
        if include_metadata:
            if not self._extract_core:
                raise ValueError("include_metadata requires extract_core=True")
            if label in self._extracted:
                metadata = {k: v.metadata for k, v in self._extracted[label].items()}
        
        return combine_dataframes(
            data,
            add_source=add_source,
            ignore_index=ignore_index,
            metadata=metadata,
            include_metadata=include_metadata
        )

    def __repr__(self):
        loaded = [l for l in self._labels if self._widgets.get(l, {}) and self._widgets[l].data]
        mode = "retain" if self._retain_data else "replace"
        return f"FileDrop(labels={self._labels}, loaded={loaded}, mode={mode})"
