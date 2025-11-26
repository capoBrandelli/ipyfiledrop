# Quick Start

Get up and running in 3 steps.

## 1. Install

```bash
pip install -e /path/to/filedrop
```

## 2. Import

```python
from jupyter_iframe_upload import FileDrop
```

## 3. Use

```python
fd = FileDrop("My Data").display()
```

Drop a CSV, XLSX, or XLSM file onto the widget, then access your DataFrame:

```python
df = fd["My Data"]
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

## Full Documentation

See [README.md](README.md) for complete API reference and troubleshooting.
