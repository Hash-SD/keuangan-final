from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .files import read_json, write_json
from .paths import ACTIVITY_LOG_PATH, LOGS_DIR, PORTAL_LOG_PATH


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

    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_line = f"[{entry['time']}] [{status.upper()}] action={action} source={source} target={target} - {message}\n"
        with open(PORTAL_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass

    return entry
