# Installation Guide

Install `jupyter-iframe-upload` from any project folder.

## Quick Install

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package (replace with actual path)
pip install -e /path/to/filedrop

# Install JupyterLab with kernel support
pip install jupyterlab ipykernel

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

### 3. Install jupyter-iframe-upload

Install the package in editable mode from the filedrop source directory:

```bash
pip install -e /path/to/filedrop
```

Or clone and install:

```bash
git clone <repo-url> /path/to/filedrop
pip install -e /path/to/filedrop
```

### 4. Install JupyterLab

```bash
pip install jupyterlab ipykernel
```

### 5. Verify Installation

```bash
python3 -c "from jupyter_iframe_upload import FileDrop; print('OK')"
```

### 6. Launch JupyterLab

```bash
jupyter lab
```

## Usage

In a Jupyter notebook:

```python
from jupyter_iframe_upload import FileDrop

# Create drop zones and display
fd = FileDrop("Train", "Test").display()

# After dropping files, access DataFrames
train_df = fd["Train"]
test_df = fd["Test"]
```

## Troubleshooting

### ModuleNotFoundError: No module named 'jupyter_iframe_upload'

- Ensure your virtual environment is activated before launching `jupyter lab`
- Ensure `ipykernel` is installed: `pip install ipykernel`
- Verify the package is installed: `pip list | grep jupyter-iframe-upload`
- Reinstall: `pip install -e /path/to/filedrop`

### Widget doesn't display in JupyterLab

- Ensure `ipywidgets` is installed: `pip install ipywidgets`
- Restart the Jupyter kernel
- Refresh the browser page

### File drops don't work

- Restart the kernel and run cells again
- Check browser console for errors (F12 → Console)
- Ensure you're using JupyterLab (not classic Notebook)

## Uninstall

```bash
pip uninstall jupyter-iframe-upload
```
