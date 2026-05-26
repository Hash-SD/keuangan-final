from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.paths import ensure_parent


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

