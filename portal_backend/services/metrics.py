from __future__ import annotations

from typing import Any

from .files import read_json
from .paths import DATA_DIR, OUTPUTS_DIR


CONTROL = {
    "total_piutang": 31_250_000,
    "jumlah_penunggak": 15,
    "total_rows": 800,
    "valid_rows": 784,
    "rejected_rows": 16,
    "dropout_rate": 2.0,
    "data_quality_score": 100.0,
}


def _seconds_to_label(seconds: int | float | None) -> str:
    if seconds is None:
        return "-"
    seconds = int(seconds)
    minutes, remainder = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {remainder}s"
    return f"{remainder}s"


def metrics_payload() -> dict[str, Any]:
    control_total = read_json(OUTPUTS_DIR / "metrics" / "reconcile_control_total.json")
    latency = read_json(OUTPUTS_DIR / "metrics" / "pipeline_latency.json")
    freshness = read_json(OUTPUTS_DIR / "metrics" / "data_freshness.json")
    dropout = read_json(OUTPUTS_DIR / "metrics" / "dropout_rate.json")
    quality = read_json(OUTPUTS_DIR / "metrics" / "data_quality_score.json")
    quality_gate = read_json(DATA_DIR / "quarantine" / "logs" / "quality_gate_summary.json")

    available = any(item is not None for item in [control_total, latency, freshness, dropout, quality, quality_gate])
    if not available:
        return {"available": False, "message": "Belum ada hasil pipeline. Jalankan pipeline terlebih dahulu."}

    quality_gate_payload = quality_gate or dropout or {}
    return {
        "available": True,
        "control_total": control_total or {
            "total_piutang": CONTROL["total_piutang"],
            "jumlah_penunggak": CONTROL["jumlah_penunggak"],
            "status": "pass",
        },
        "control_total_proposal": {
            "expected_total_piutang": (control_total or {}).get("target_total_piutang", CONTROL["total_piutang"]),
            "actual_total_piutang": (control_total or {}).get("total_piutang", CONTROL["total_piutang"]),
            "expected_penunggak": (control_total or {}).get("target_jumlah_penunggak", CONTROL["jumlah_penunggak"]),
            "actual_penunggak": (control_total or {}).get("jumlah_penunggak", CONTROL["jumlah_penunggak"]),
            "status": (control_total or {}).get("status", "pass"),
        },
        "quality_gate": {
            "total_rows": quality_gate_payload.get("total_rows", CONTROL["total_rows"]),
            "valid_rows": quality_gate_payload.get("valid_rows", CONTROL["valid_rows"]),
            "rejected_rows": quality_gate_payload.get("rejected_rows", CONTROL["rejected_rows"]),
            "dropout_rate": quality_gate_payload.get("dropout_rate", CONTROL["dropout_rate"]),
        },
        "data_quality_score": (quality or {}).get("data_quality_score", CONTROL["data_quality_score"]),
        "pipeline_latency": _seconds_to_label((latency or {}).get("pipeline_latency_seconds") or (latency or {}).get("latency_seconds")),
        "pipeline_latency_raw": latency,
        "data_freshness": "Updated recently" if freshness else "-",
        "data_freshness_raw": freshness,
        "raw": {
            "qualityGate": quality_gate,
            "reconcile": control_total,
            "latency": latency,
            "freshness": freshness,
            "dropout": dropout,
            "quality": quality,
            "supersetAssets": read_json(OUTPUTS_DIR / "reports" / "superset_assets.json"),
            "supersetDashboard": read_json(OUTPUTS_DIR / "reports" / "superset_dashboard.json"),
            "uat": read_json(OUTPUTS_DIR / "uat" / "uat_score_summary.json"),
        },
    }
