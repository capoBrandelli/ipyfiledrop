"""
FileDrop - Compact multi-file drop widget for Jupyter notebooks.

Provides a high-level API for multiple drop zones with automatic
global listener installation and DataFrame access.
"""

import logging
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
        self._datasets = {}     # label -> {'filename': str, 'df': DataFrame}
        self._labels = []       # Ordered list of labels
        self._container = widgets.VBox()  # Main container for embedding

        # Create initial widgets
        for label in labels:
            self._add_widget(label)

        # Build initial UI
        self._update_ui()

    def _add_widget(self, label):
        """Create IFrameDropWidget for a label with callback."""
        def on_dataframe_ready(filename, df):
            self._datasets[label] = {'filename': filename, 'df': df}
            logger.debug(f"FileDrop: Loaded '{filename}' into '{label}'")

        widget = IFrameDropWidget(on_dataframe_ready=on_dataframe_ready)
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
        Get DataFrame by label.

        Args:
            label: Drop zone label

        Returns:
            pandas.DataFrame or None if no file loaded

        Raises:
            KeyError: If label doesn't exist
        """
        if label not in self._widgets:
            raise KeyError(f"Label '{label}' not found")
        data = self._datasets.get(label)
        return data['df'] if data else None

    @property
    def datasets(self):
        """
        Get all loaded datasets.

        Returns:
            dict: {label: {'filename': str, 'df': DataFrame}} for loaded files
        """
        return {k: v.copy() for k, v in self._datasets.items()}

    def __repr__(self):
        loaded = [l for l in self._labels if l in self._datasets]
        return f"FileDrop(labels={self._labels}, loaded={loaded})"
