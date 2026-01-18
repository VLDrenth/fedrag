#!/usr/bin/env python3
"""CLI entry point for Fed document scraper.

This script provides a convenient way to run the scraper without
installing the package. For installed usage, use `fedrag` command.
"""

import sys
from pathlib import Path

# Add src to path for direct execution
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from fedrag.cli import app

if __name__ == "__main__":
    app()
