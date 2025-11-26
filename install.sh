#!/bin/bash
# Installation script for jupyter-iframe-upload
# Run this from your project folder

set -e

FILEDROP_PATH="/home/lukas/AI/claude/filedrop"

echo "=== Installing jupyter-iframe-upload ==="

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing filedrop package..."
pip install -e "$FILEDROP_PATH"

echo "Installing JupyterLab and ipykernel..."
pip install jupyterlab ipykernel

echo ""
echo "=== Installation complete! ==="
echo ""
echo "To use:"
echo "  source venv/bin/activate"
echo "  jupyter lab"
echo ""
echo "In a notebook:"
echo "  from jupyter_iframe_upload import FileDrop"
echo "  fd = FileDrop('My Data').display()"
