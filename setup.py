from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ipyfiledrop",
    version="1.0.0",
    author="",
    description="Drag-and-drop file upload widget for JupyterLab",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "ipywidgets>=7.0.0",
        "pandas>=1.0.0",
        "openpyxl>=3.0.0",
        "pyarrow>=8.0.0",
        "xlrd>=2.0.0",
        "jupyterlab>=3.0.0",
        "ipykernel>=6.0.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Jupyter",
    ],
)
