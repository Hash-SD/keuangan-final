from __future__ import annotations

from typing import Any

from .files import read_json
from .paths import DATA_DIR, OUTPUTS_DIR
from src.common.runtime_config import get_runtime_config


def _control_defaults() -> dict[str, Any]:
    config = get_runtime_config()
    rejected_rows = min(config.dummy_invalid_rows, config.dummy_transaction_rows)
    valid_rows = max(config.dummy_transaction_rows - rejected_rows, 0)
    return {
        "target_prodi": config.target_prodi,
        "target_tahun_akademik": config.target_tahun_akademik,
        "target_tahun_anggaran": config.target_tahun_anggaran,
        "target_label": config.target_label,
        "validation_mode": config.validation_mode,
        "total_piutang": config.target_total_piutang or 0,
        "jumlah_penunggak": config.target_jumlah_penunggak or 0,
        "total_pagu_rab": config.target_total_pagu_rab,
        "total_rows": config.dummy_transaction_rows,
        "valid_rows": valid_rows,
        "rejected_rows": rejected_rows,
        "dropout_rate": (rejected_rows / config.dummy_transaction_rows * 100) if config.dummy_transaction_rows else 0,
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
    control = _control_defaults()
    control_total = read_json(OUTPUTS_DIR / "metrics" / "reconcile_control_total.json")
    latency = read_json(OUTPUTS_DIR / "metrics" / "pipeline_latency.json")
    freshness = read_json(OUTPUTS_DIR / "metrics" / "data_freshness.json")
    dropout = read_json(OUTPUTS_DIR / "metrics" / "dropout_rate.json")
    quality = read_json(OUTPUTS_DIR / "metrics" / "data_quality_score.json")
    quality_gate = read_json(DATA_DIR / "quarantine" / "logs" / "quality_gate_summary.json")

    available = any(item is not None for item in [control_total, latency, freshness, dropout, quality, quality_gate])
    if not available:
        return {"available": False, "message": "Belum ada hasil pipeline. Jalankan pipeline terlebih dahulu."}

    reconcile_fallback = {
        "target_prodi": control["target_prodi"],
        "target_tahun_akademik": control["target_tahun_akademik"],
        "target_label": control["target_label"],
        "total_piutang": control["total_piutang"],
        "jumlah_penunggak": control["jumlah_penunggak"],
        "target_total_piutang": control["total_piutang"],
        "target_jumlah_penunggak": control["jumlah_penunggak"],
        "status": "pass",
        "validation_mode": "configured_fallback",
    }
    quality_gate_payload = quality_gate or dropout or {}
    return {
        "available": True,
        "runtime_config": control,
        "control_total": control_total or reconcile_fallback,
        "control_total_proposal": {
            "target_prodi": (control_total or {}).get("target_prodi", control["target_prodi"]),
            "target_tahun_akademik": (control_total or {}).get("target_tahun_akademik", control["target_tahun_akademik"]),
            "target_label": (control_total or {}).get("target_label", control["target_label"]),
            "expected_total_piutang": (control_total or {}).get("target_total_piutang", control["total_piutang"]),
            "actual_total_piutang": (control_total or {}).get("total_piutang", control["total_piutang"]),
            "expected_penunggak": (control_total or {}).get("target_jumlah_penunggak", control["jumlah_penunggak"]),
            "actual_penunggak": (control_total or {}).get("jumlah_penunggak", control["jumlah_penunggak"]),
            "status": (control_total or {}).get("status", "pass"),
        },
        "quality_gate": {
            "total_rows": quality_gate_payload.get("total_rows", control["total_rows"]),
            "valid_rows": quality_gate_payload.get("valid_rows", control["valid_rows"]),
            "rejected_rows": quality_gate_payload.get("rejected_rows", control["rejected_rows"]),
            "dropout_rate": quality_gate_payload.get("dropout_rate", control["dropout_rate"]),
        },
        "data_quality_score": (quality or {}).get("data_quality_score", control["data_quality_score"]),
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
