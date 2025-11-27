"""
FileDrop - Compact multi-file drop widget for Jupyter notebooks.

Provides a high-level API for multiple drop zones with automatic
global listener installation and DataFrame access.
"""

import logging
from typing import Dict, Optional
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from .iframe_drop_widget import IFrameDropWidget

logger = logging.getLogger(__name__)


class FileDrop:
    """
    Compact multi-file drop widget manager.

    Creates multiple drop zones with automatic global listener installation.
    Files are automatically parsed to pandas DataFrames.

    Example:
        fd = FileDrop("Train", "Test").display()
        df_train = fd["Train"]  # Returns DataFrame or None
        fd.add("Validation")
        fd.remove("Test")
        
        # Multi-sheet Excel support
        all_sheets = fd.get_all_sheets("Train")
        fd.select_sheet("Train", "Sheet2")
    """

    def __init__(self, *labels):
        """
        Initialize FileDrop with named drop zones.

        Args:
            *labels: Variable number of drop zone labels (e.g., "Train", "Test")
        """
        # Auto-install global listener (safe if already installed)
        IFrameDropWidget.install_global_listener()

        self._widgets = {}      # label -> IFrameDropWidget
        self._datasets = {}     # label -> {'filename': str, 'data': Dict[str, DataFrame], 'selected': str}
        self._labels = []       # Ordered list of labels
        self._container = widgets.VBox()  # Main container for embedding

        # Create initial widgets
        for label in labels:
            self._add_widget(label)

        # Build initial UI
        self._update_ui()

    def _add_widget(self, label):
        """Create IFrameDropWidget for a label with callback."""
        def on_data_ready(filename, data):
            self._datasets[label] = {
                'filename': filename, 
                'data': data,
                'selected': list(data.keys())[0]
            }
            logger.debug(f"FileDrop: Loaded '{filename}' into '{label}' ({len(data)} sheet(s))")

        widget = IFrameDropWidget(on_data_ready=on_data_ready)
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

    def get_all_sheets(self, label) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Get all DataFrames for a label (all sheets for Excel files).

        Args:
            label: Drop zone label

        Returns:
            Dict[str, DataFrame] or None if no file loaded

        Raises:
            KeyError: If label doesn't exist
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        dataset = self._datasets.get(label)
        return dataset['data'] if dataset else None

    def select_sheet(self, label: str, sheet_name: str) -> 'FileDrop':
        """
        Select a specific sheet for a label.

        Args:
            label: Drop zone label
            sheet_name: Name of sheet to select

        Returns:
            FileDrop: self for method chaining

        Raises:
            KeyError: If label doesn't exist
            ValueError: If no data loaded or sheet not found
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        dataset = self._datasets.get(label)
        if not dataset:
            raise ValueError(f"No data loaded for '{label}'")
        if sheet_name not in dataset['data']:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available: {list(dataset['data'].keys())}")
        
        self._widgets[label]._selector.value = sheet_name
        return self

    @property
    def datasets(self):
        """
        Get all loaded datasets.

        Returns:
            dict: {label: {'filename': str, 'data': Dict[str, DataFrame], 'selected': str}} for loaded files
        """
        return {k: {
            'filename': v['filename'],
            'data': {sk: sv.copy() for sk, sv in v['data'].items()},
            'selected': self._widgets[k].selected_key or v['selected']
        } for k, v in self._datasets.items()}

    def __repr__(self):
        loaded = [l for l in self._labels if l in self._datasets]
        return f"FileDrop(labels={self._labels}, loaded={loaded})"
