# ipyfiledrop

A drag-and-drop file upload widget for JupyterLab.

**Features:**
- Drop single or multiple files at once
- Archive support (.zip, .tar.gz) with automatic extraction
- Multi-sheet Excel support with dropdown selector
- Accumulate mode for building datasets incrementally

## Installation

```bash
# Clone or download the repository
git clone <repo-url>
cd filedrop

# Install as editable package
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

## Quick Start

```python
from ipyfiledrop import FileDrop

# One-line creation and display
fd = FileDrop("Dataset A", "Dataset B").display()

# Access loaded DataFrames
df = fd["Dataset A"]  # Returns DataFrame or None

# Dynamic management
fd.add("Dataset C")
fd.remove("Dataset A")
```

### Multi-File Drop & Archives

```python
# Accumulate mode - files stack up instead of replacing
fd = FileDrop("Data", retain_data=True).display()

# Drop multiple files at once, or drop a .zip/.tar.gz archive
# All files are extracted and accumulated

# Access all loaded data
all_data = fd.get_all_data("Data")  # Dict[str, DataFrame]

# Clear accumulated data
fd.clear("Data")
```

See [QUICKSTART.md](QUICKSTART.md) for a minimal getting-started guide.

## How it works

This widget creates an iframe with its own isolated document context. The iframe handles drag-drop events internally, reads files as base64, and communicates with the parent window via `postMessage`. Hidden ipywidgets bridge the JavaScript events to Python callbacks.

## API Reference

### FileDrop (Recommended)

Compact API for multiple file drop zones.

```python
from ipyfiledrop import FileDrop

# Create with named drop zones
fd = FileDrop("Train", "Test", "Validation").display()

# Access data
fd["Train"]      # Returns DataFrame or None
fd.datasets      # Returns dict of all loaded data

# Dynamic management
fd.add("Extra")        # Add new drop zone
fd.remove("Test")      # Remove zone and clear data
```

**Constructor:**
- `FileDrop(*labels, retain_data=False, extract_core=False, clean=None, cleaner=None, cleaners=None)`
  - `retain_data=True`: Files accumulate (useful for multi-file drops)
  - `retain_data=False` (default): Each drop replaces previous data
  - `extract_core=True`: Automatically extract core data from messy files
  - `clean`: Cleaning preset (`'none'`, `'minimal'`, `'standard'`, `'aggressive'`)
  - `cleaner`: Custom cleaner function `(df, filename) -> df`
  - `cleaners`: List of cleaner functions to apply in sequence

**Methods:**
- `display()` → Returns self for chaining
- `add(label)` → Add drop zone, returns self
- `remove(label)` → Remove zone and data, returns self
- `clear(label)` → Clear all data for a zone, returns self
- `__getitem__(label)` → Get selected DataFrame by label
- `get_all_data(label)` → Get all DataFrames as Dict[str, DataFrame]
- `get_all_sheets(label)` → Alias for get_all_data()
- `select_sheet(label, sheet_name)` → Select a specific sheet/file
- `get_failed_imports(label)` → Get list of files that failed to import
- `extract(label)` → Get ExtractedData with core, metadata, footer (requires `extract_core=True`)
- `combine(label, add_source=False)` → Combine all DataFrames into one

**Properties:**
- `datasets` → Dict of `{label: {'filename': str, 'data': Dict[str, DataFrame], 'selected': str}}`
- `ui` → Widget for embedding in containers (see below)
- `retain_data` → Whether accumulate mode is enabled

### Embedding in Containers

Use the `.ui` property to embed FileDrop in ipywidgets containers like Accordion, Tab, or VBox:

```python
import ipywidgets as widgets
from ipyfiledrop import FileDrop

# Accordion
fd = FileDrop("Train", "Test")
accordion = widgets.Accordion(children=[fd.ui])
accordion.set_title(0, "Data Upload")
display(accordion)

# Tab
fd1 = FileDrop("CSV Files")
fd2 = FileDrop("Excel Files")
tab = widgets.Tab(children=[fd1.ui, fd2.ui])
tab.set_title(0, "CSV")
tab.set_title(1, "Excel")
display(tab)

# VBox with other widgets
fd = FileDrop("Upload")
btn = widgets.Button(description="Process")
vbox = widgets.VBox([fd.ui, btn])
display(vbox)
```

### IFrameDropWidget (Low-level)

For single drop zones with custom callbacks.

```python
from ipyfiledrop import IFrameDropWidget

# Install global listener first
IFrameDropWidget.install_global_listener()

# Create widget with callback (receives Dict of DataFrames)
def handle_data(filename, data):
    # data is Dict[str, DataFrame] - keys are sheet names for Excel, 'data' for others
    for key, df in data.items():
        print(f"Loaded: {filename}[{key}], shape: {df.shape}")

# Single file mode (default) - each drop replaces previous
widget = IFrameDropWidget(on_data_ready=handle_data)

# Multi-file mode - files accumulate
widget = IFrameDropWidget(on_data_ready=handle_data, retain_data=True)

widget.display()

# Access data via properties
widget.data              # Dict[str, DataFrame] - all loaded data
widget.selected_dataframe  # Currently selected DataFrame
widget.keys              # List of all data keys
widget.failed_imports    # List of files that failed to import

# Clear accumulated data
widget.clear_data()
```

**Note:** `install_global_listener()` must be called BEFORE creating widgets. FileDrop handles this automatically.

## Data Import Pipeline

For messy files with headers, footers, and sparse data, use the data import pipeline to automatically extract, clean, and combine data.

### Basic Usage

```python
from ipyfiledrop import FileDrop

# Enable extraction and cleaning
fd = FileDrop(
    "Messy Data",
    retain_data=True,        # Accumulate files
    extract_core=True,       # Extract core data from messy files
    clean="standard",        # Apply standard cleaning
).display()

# After dropping files:
extracted = fd.extract("Messy Data")
extracted.core        # Clean DataFrame
extracted.metadata    # {'Report Date': '2024-01-15', ...}
extracted.footer      # ['End of Report', ...]
extracted.confidence  # 0.90

# Combine multiple files
df = fd.combine("Messy Data", add_source=True)
```

### Cleaning Presets

| Preset | Cleaners Applied |
|--------|------------------|
| `'none'` | No cleaning |
| `'minimal'` | normalize_columns, strip_whitespace |
| `'standard'` | normalize_columns, strip_whitespace, drop_empty_rows, standardize_na |
| `'aggressive'` | All cleaners including deduplicate, infer_types |

### Custom Cleaners

```python
from ipyfiledrop import (
    normalize_columns, make_normalize_columns,
    strip_whitespace, make_strip_whitespace,
    drop_empty_rows
)

# Use factory functions for customized cleaners
fd = FileDrop("Data", cleaners=[
    make_normalize_columns(preserve_case=True, preserve_dashes=True),
    make_strip_whitespace(normalize_inner=True),
    drop_empty_rows
])
```

### Cleaner Options

**`normalize_columns`** options:
- `preserve_case=True`: Keep original case (default: lowercase)
- `preserve_dashes=True`: Keep dashes `-` (default: replace with `_`)
- `preserve_dots=True`: Keep dots `.` (default: replace with `_`)

**`strip_whitespace`** options:
- `normalize_inner=True`: Collapse multiple inner spaces to single space

### Direct Pipeline Functions

```python
from ipyfiledrop import extract_core_data, clean_dataframe, combine_dataframes
import pandas as pd

# Load messy file
raw = pd.read_csv('messy_file.csv', header=None)

# Extract core data
result = extract_core_data(raw)
print(result.core.shape)      # (21, 6)
print(result.metadata)        # {'Report Date': '2024-01-15'}

# Clean
cleaned = clean_dataframe(result.core, preset='standard')

# Combine multiple DataFrames
combined = combine_dataframes({'file1': df1, 'file2': df2}, add_source=True)
```

## Supported Files

| Format | Extension | Required Package |
|--------|-----------|------------------|
| CSV | `.csv` | pandas (included) |
| Excel (modern) | `.xlsx`, `.xlsm` | openpyxl (included) |
| Excel (legacy) | `.xls` | xlrd (included) |
| Feather | `.feather` | pyarrow (included) |
| Parquet | `.parquet` | pyarrow (included) |
| ZIP archive | `.zip` | (built-in) |
| TAR archive | `.tar.gz`, `.tgz` | (built-in) |

**Notes:**
- Excel files with multiple sheets are fully supported. A dropdown selector appears to switch between sheets.
- Archives are automatically extracted; all supported files inside are loaded.
- Maximum file size: 200MB per file
- Maximum files per drop: 50 files
- Maximum total files (retain_data=True): 1000 files
- Files are processed in-memory (no disk writes)

## How It Works

1. An iframe with `srcdoc` creates an isolated document context
2. The iframe handles drag-drop events independently from Lumino
3. Files are read as base64 and sent via `postMessage`
4. A global JavaScript listener updates hidden ipywidgets
5. Python observers parse files into DataFrames

## Troubleshooting

### Widget doesn't respond to drops
- Restart kernel and try again
- Check browser console for "GLOBAL: IFrame drop listener installed"

### File parsing errors
- Ensure `openpyxl` is installed for Excel support
- Check file is valid CSV/XLSX/XLSM

### Missing dependency errors

If you see an error like:
```
Cannot read .parquet file: 'pyarrow' is not installed.
```

**Solution:**

1. **Check which dependencies are available:**
   ```python
   from ipyfiledrop import IFrameDropWidget
   
   deps = IFrameDropWidget.check_dependencies()
   for name, info in deps.items():
       status = "OK" if info['available'] else "MISSING"
       print(f"{name}: {status} - needed for {info['required_for']}")
   ```

2. **Install the missing dependency in your notebook:**
   ```python
   # For .feather or .parquet files
   !pip install pyarrow
   
   # For .xls files (legacy Excel)
   !pip install xlrd
   
   # For .xlsx/.xlsm files
   !pip install openpyxl
   ```

3. **Restart the kernel** after installing new packages

**Note:** Dependencies must be installed in the same Python environment as your Jupyter kernel. If `!pip install` doesn't work, you may need to install from a terminal using the correct Python:
```bash
# Find your kernel's Python
python -m pip install pyarrow
```

## License

MIT License
