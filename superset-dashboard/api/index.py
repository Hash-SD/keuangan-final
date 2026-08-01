from __future__ import annotations

import sys
from pathlib import Path

# Allow `from server import create_app` to resolve lib/_shared.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import create_app  # noqa: E402

app = create_app()
