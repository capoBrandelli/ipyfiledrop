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

**Supported formats:** CSV, Excel (.xlsx, .xlsm, .xls), Feather, Parquet

**Multi-sheet Excel:** A dropdown appears to select sheets. Access all sheets with:
```python
all_sheets = fd.get_all_sheets("My Data")  # Dict[str, DataFrame]
```

---

## Multiple Files

```python
fd = FileDrop("Train", "Test").display()

# After dropping files:
train_df = fd["Train"]
test_df = fd["Test"]
```

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
