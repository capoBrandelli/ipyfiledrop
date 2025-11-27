# Installation Guide

Install `ipyfiledrop` from any project folder.

## Quick Install

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package (includes JupyterLab, ipykernel, and all dependencies)
pip install -e /path/to/filedrop

# Launch
jupyter lab
```

## Step-by-Step Installation

### 1. Create a Virtual Environment

Navigate to your project folder and create a virtual environment:

```bash
cd /path/to/your/project
python3 -m venv venv
```

### 2. Activate the Virtual Environment

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install ipyfiledrop

Install the package in editable mode from the filedrop source directory:

```bash
pip install -e /path/to/filedrop
```

Or clone and install:

```bash
git clone <repo-url> /path/to/filedrop
pip install -e /path/to/filedrop
```

This automatically installs all dependencies (if not installed already):
- `jupyterlab` and `ipykernel` - Jupyter environment
- `ipywidgets` - Widget framework
- `pandas`, `openpyxl`, `xlrd` - Data processing and Excel support
- `pyarrow` - Feather and Parquet support

### 4. Verify Installation

```bash
python3 -c "from ipyfiledrop import FileDrop; print('OK')"
```

### 5. Launch JupyterLab

```bash
jupyter lab
```

## Supported File Formats

| Format | Extensions |
|--------|------------|
| CSV | `.csv` |
| Excel | `.xlsx`, `.xlsm`, `.xls` |
| Feather | `.feather` |
| Parquet | `.parquet` |

Multi-sheet Excel files are supported with a dropdown selector.

## Usage

In a Jupyter notebook:

```python
from ipyfiledrop import FileDrop

# Create drop zones and display
fd = FileDrop("Train", "Test").display()

# After dropping files, access DataFrames
train_df = fd["Train"]
test_df = fd["Test"]

# For multi-sheet Excel files
all_sheets = fd.get_all_sheets("Train")  # Dict[str, DataFrame]
fd.select_sheet("Train", "Sheet2")       # Select specific sheet
```

## Troubleshooting

### ModuleNotFoundError: No module named 'ipyfiledrop'

- Ensure your virtual environment is activated before launching `jupyter lab`
- Verify the package is installed: `pip list | grep ipyfiledrop`
- Reinstall: `pip install -e /path/to/filedrop`

### Widget doesn't display in JupyterLab

- Restart the Jupyter kernel
- Refresh the browser page

### File drops don't work

- Restart the kernel and run cells again
- Check browser console for errors (F12 → Console)
- Ensure you're using JupyterLab (not classic Notebook)

### Missing dependency errors

Check dependencies in your notebook:
```python
from ipyfiledrop import IFrameDropWidget
deps = IFrameDropWidget.check_dependencies()
for name, info in deps.items():
    status = "OK" if info['available'] else "MISSING"
    print(f"{name}: {status}")
```

If any are missing, reinstall the package or install individually with `!pip install <package>`

## Uninstall

```bash
pip uninstall ipyfiledrop
```
