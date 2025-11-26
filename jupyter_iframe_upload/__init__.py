"""
Jupyter IFrame Upload - Drag-and-drop file upload for JupyterLab

A widget that enables drag-and-drop file uploads by using an iframe
to bypass JupyterLab's Lumino event interception.
"""

from .iframe_drop_widget import IFrameDropWidget
from .filedrop import FileDrop

__all__ = ['IFrameDropWidget', 'FileDrop']
__version__ = '1.0.0'
