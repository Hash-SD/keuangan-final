from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from src.common.paths import ensure_parent


def write_text(path: Path, content: str) -> None:
    """Write a text artifact atomically, including over a read-only target.

    Runtime output directories are shared by containers that can use different
    UIDs. Writing a temporary sibling and replacing the target avoids requiring
    write permission on an existing file owned by another process, while the
    writable directory still remains the required boundary.
    """
    ensure_parent(path)
    target_mode = 0o644
    try:
        target_mode = stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR
    except OSError:
        pass

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(content)
        os.chmod(temporary_name, target_mode)
        try:
            os.replace(temporary_name, path)
        except PermissionError:
            # Windows can retain a read-only attribute on an existing target;
            # clear only the write bit needed for this replacement and retry.
            writable_mode = stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR
            os.chmod(path, writable_mode)
            os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))
