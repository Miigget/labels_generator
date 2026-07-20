#!/usr/bin/env python3
"""Project-root launcher for ``python main.py``."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as ``python main.py`` from the project root without installing.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from generator.main import main

if __name__ == "__main__":
    raise SystemExit(main())
