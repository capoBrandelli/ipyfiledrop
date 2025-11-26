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
        self._output = widgets.Output()

        # Create initial widgets
        for label in labels:
            self._add_widget(label)

    def _add_widget(self, label):
        """Create IFrameDropWidget for a label with callback."""
        def on_dataframe_ready(filename, df):
            self._datasets[label] = {'filename': filename, 'df': df}
            logger.debug(f"FileDrop: Loaded '{filename}' into '{label}'")

        widget = IFrameDropWidget(on_dataframe_ready=on_dataframe_ready)
        self._widgets[label] = widget
        self._labels.append(label)

    def _render(self):
        """Render all drop zones in horizontal layout."""
        with self._output:
            self._output.clear_output(wait=True)

            if not self._widgets:
                display(widgets.HTML("<p>No drop zones</p>"))
                return

            # Create VBox for each label with header
            boxes = []
            for label in self._labels:
                if label in self._widgets:
                    header = widgets.HTML(f"<h4 style='margin:0 0 5px 0'>{label}</h4>")
                    box = widgets.VBox([header, self._widgets[label].widget])
                    boxes.append(box)

            # Display horizontally
            hbox = widgets.HBox(boxes)
            display(hbox)

    def display(self):
        """
        Display the widget and return self for chaining.

        Returns:
            FileDrop: self for method chaining
        """
        self._render()
        display(self._output)
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
        self._render()
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
        self._render()
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
