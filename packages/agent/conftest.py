"""Make the agent package importable from the source tree.

The package is normally installed into the project virtual environment; this
shim keeps the test suite runnable straight from a checkout, without touching
the environment of anybody else.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"

if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
