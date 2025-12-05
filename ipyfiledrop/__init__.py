"""
ipyfiledrop - Drag-and-drop file upload widget for JupyterLab

A widget that enables drag-and-drop file uploads by using an iframe
to bypass JupyterLab's Lumino event interception.

Includes data import pipeline for extracting, cleaning, and combining DataFrames.
"""

from .iframe_drop_widget import IFrameDropWidget
from .filedrop import FileDrop
from .pipeline import (
    ExtractedData,
    extract_core_data,
    clean_dataframe,
    combine_dataframes,
    CLEANING_PRESETS,
    # Individual cleaners for custom pipelines
    normalize_columns,
    make_normalize_columns,
    strip_whitespace,
    make_strip_whitespace,
    drop_empty_rows,
    drop_empty_cols,
    standardize_na,
    deduplicate,
    infer_types,
)

__all__ = [
    # Widgets
    'IFrameDropWidget', 
    'FileDrop', 
    # Pipeline
    'ExtractedData',
    'extract_core_data',
    'clean_dataframe',
    'combine_dataframes',
    'CLEANING_PRESETS',
    # Individual cleaners
    'normalize_columns',
    'make_normalize_columns',
    'strip_whitespace',
    'make_strip_whitespace',
    'drop_empty_rows',
    'drop_empty_cols',
    'standardize_na',
    'deduplicate',
    'infer_types',
    # Version
    '__version__', 
    'version',
]
__version__ = '1.1.0'


def version():
    """Return version information as a formatted string."""
    return f"ipyfiledrop {__version__}"
