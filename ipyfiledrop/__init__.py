"""
ipyfiledrop - Drag-and-drop file upload widget for JupyterLab

A widget that enables drag-and-drop file uploads by using an iframe
to bypass JupyterLab's Lumino event interception.
"""

from .iframe_drop_widget import IFrameDropWidget
from .filedrop import FileDrop

__all__ = ['IFrameDropWidget', 'FileDrop', '__version__', 'version']
__version__ = '1.0.0'


def version():
    """Return version information as a formatted string."""
    return f"ipyfiledrop {__version__}"
