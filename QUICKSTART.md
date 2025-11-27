# Quick Start

Get up and running in 3 steps.

## 1. Install

```bash
pip install -e /path/to/filedrop
```

## 2. Import

```python
from ipyfiledrop import FileDrop
```

## 3. Use

```python
fd = FileDrop("My Data").display()
```

Drop a file onto the widget, then access your DataFrame:

```python
df = fd["My Data"]
```

**Supported formats:** CSV, Excel (.xlsx, .xlsm, .xls), Feather, Parquet, ZIP, TAR.GZ

**Multi-sheet Excel:** A dropdown appears to select sheets. Access all sheets with:
```python
all_sheets = fd.get_all_sheets("My Data")  # Dict[str, DataFrame]
```

---

## Multiple Drop Zones

```python
fd = FileDrop("Train", "Test").display()

# After dropping files:
train_df = fd["Train"]
test_df = fd["Test"]
```

## Multi-File Drop & Archives

Drop multiple files at once or drop a .zip/.tar.gz archive:

```python
# Accumulate mode - files stack up instead of replacing
fd = FileDrop("Data", retain_data=True).display()

# Drop multiple files or an archive - all are loaded
all_data = fd.get_all_data("Data")  # Dict[str, DataFrame]

# Check for failed imports
failed = fd.get_failed_imports("Data")

# Clear and start fresh
fd.clear("Data")
```

**Limits:** 200MB per file, 50 files per drop, 1000 files total

## Dynamic Add/Remove

```python
fd.add("Validation")   # Add new drop zone
fd.remove("Test")      # Remove zone and data
```

## Embedding in Containers

Use `.ui` to embed in Accordion, Tab, or other containers:

```python
import ipywidgets as widgets

fd = FileDrop("Train", "Test")
accordion = widgets.Accordion(children=[fd.ui])
accordion.set_title(0, "Data Upload")
display(accordion)
```

## Full Documentation

See [README.md](README.md) for complete API reference and troubleshooting.
