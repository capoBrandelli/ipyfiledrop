"""
Command-line interface for ipyfiledrop.

Usage:
    python -m ipyfiledrop --version
    python -m ipyfiledrop --check
"""

import argparse
import sys

from . import __version__, IFrameDropWidget


def main():
    parser = argparse.ArgumentParser(
        prog='ipyfiledrop',
        description='Drag-and-drop file upload widget for JupyterLab'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'ipyfiledrop {__version__}'
    )
    parser.add_argument(
        '-c', '--check',
        action='store_true',
        help='Check if all dependencies are installed'
    )
    
    args = parser.parse_args()
    
    if args.check:
        deps = IFrameDropWidget.check_dependencies()
        all_ok = True
        print(f"ipyfiledrop {__version__}\n")
        print("Dependencies:")
        for name, info in deps.items():
            if info['available']:
                print(f"  ✓ {name} {info['version']} - {info['required_for']}")
            else:
                print(f"  ✗ {name} MISSING - {info['required_for']}")
                all_ok = False
        print()
        if all_ok:
            print("All dependencies OK!")
        else:
            print("Some dependencies are missing. Install with: pip install ipyfiledrop")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
