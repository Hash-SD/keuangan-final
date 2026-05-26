from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def batch_id() -> str:
    return datetime.now(timezone.utc).strftime("batch-%Y%m%d%H%M%S")

