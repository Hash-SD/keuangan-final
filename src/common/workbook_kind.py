"""Consistent workbook-kind inference at upload and pipeline boundaries."""

from __future__ import annotations

import re
from pathlib import Path


KNOWN_WORKBOOK_KINDS = frozenset({"rab", "rpd", "iku", "nomenklatur"})
_RAB_NAME_PATTERN = re.compile(r"(?:^|[^a-z])rab(?:[^a-z]|$)")


def infer_workbook_kind(filename: str | Path, explicit: object = None) -> str:
    """Infer a workbook kind, correcting obvious copied category metadata."""

    name = Path(str(filename)).name.casefold()
    explicit_kind = str(explicit or "").strip().casefold()
    if "nomenklatur" in name:
        return "nomenklatur"
    if explicit_kind in KNOWN_WORKBOOK_KINDS:
        if explicit_kind == "nomenklatur" and (
            "anggaran" in name or _RAB_NAME_PATTERN.search(name)
        ):
            return "rab"
        return explicit_kind
    if "anggaran" in name or _RAB_NAME_PATTERN.search(name):
        return "rab"
    return "rab"
