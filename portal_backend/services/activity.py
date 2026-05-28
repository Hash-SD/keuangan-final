from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .files import read_json, write_json
from .paths import ACTIVITY_LOG_PATH


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S")


def read_activities() -> dict[str, Any]:
    payload = read_json(ACTIVITY_LOG_PATH)
    if payload is None:
        return {"activities": [], "message": "Belum ada aktivitas tercatat."}
    if isinstance(payload, list):
        return {"activities": payload}
    return {"activities": payload.get("activities", []), "message": payload.get("message")}


def append_activity(action: str, source: str, status: str, message: str, target: str = "") -> dict[str, str]:
    entry = {
        "time": _now(),
        "actor": "system",
        "action": action,
        "source": source,
        "target": target,
        "status": status,
        "message": message,
    }
    current = read_activities().get("activities", [])
    current.insert(0, entry)
    write_json(ACTIVITY_LOG_PATH, {"activities": current[:100]})
    return entry
