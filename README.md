# Jupyter File Drag & Drop Widget

A drag-and-drop file upload widget for JupyterLab.

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

**Methods:**
- `display()` → Returns self for chaining
- `add(label)` → Add drop zone, returns self
- `remove(label)` → Remove zone and data, returns self
- `__getitem__(label)` → Get DataFrame by label

**Properties:**
- `datasets` → Dict of `{label: {'filename': str, 'data': Dict[str, DataFrame], 'selected': str}}`
- `ui` → Widget for embedding in containers (see below)

**Multi-sheet Excel methods:**
- `get_all_sheets(label)` → Get all sheets as Dict[str, DataFrame]
- `select_sheet(label, sheet_name)` → Select a specific sheet

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
    for sheet_name, df in data.items():
        print(f"Loaded: {filename}[{sheet_name}], shape: {df.shape}")

widget = IFrameDropWidget(on_data_ready=handle_data)
widget.display()

# Access data via properties
widget.data              # Dict[str, DataFrame] or None
widget.selected_dataframe  # Currently selected DataFrame
widget.sheet_names       # List of available sheet/data names
```

**Note:** `install_global_listener()` must be called BEFORE creating widgets. FileDrop handles this automatically.

## Supported Files

| Format | Extension | Required Package |
|--------|-----------|------------------|
| CSV | `.csv` | pandas (included) |
| Excel (modern) | `.xlsx`, `.xlsm` | openpyxl (included) |
| Excel (legacy) | `.xls` | xlrd (included) |
| Feather | `.feather` | pyarrow (included) |
| Parquet | `.parquet` | pyarrow (included) |

**Note:** Excel files with multiple sheets are fully supported. A dropdown selector appears to switch between sheets.

- Maximum file size: 50MB
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
