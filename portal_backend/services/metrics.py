from __future__ import annotations

from typing import Any

from src.status.system_truth_status import build_system_truth_status

def _unwrap(item: dict[str, Any] | None) -> Any:
    if not isinstance(item, dict):
        return None
    return item.get("value") if item.get("status") in {"validated", "completed"} else None


def _latency_value(latency: dict[str, Any]) -> Any:
    for key in ["pipeline_latency_seconds", "latency_seconds", "elapsed_seconds"]:
        item = latency.get(key)
        if isinstance(item, dict) and item.get("status") in {"validated", "running"}:
            return item.get("value")
    return None


def _seconds_to_label(seconds: int | float | None) -> str:
    if seconds is None:
        return "-"
    seconds = int(seconds)
    minutes, remainder = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {remainder}s"
    return f"{remainder}s"


def metrics_payload() -> dict[str, Any]:
    truth = build_system_truth_status(write_outputs=True)
    quality_gate = truth["quality_gate"]
    reconcile = truth["reconciliation"]
    latency = truth["metrics"]["pipeline_latency"]
    freshness = truth["metrics"]["data_freshness"]
    uat = truth["uat"]

    available = any(
        item.get("status") in {"validated", "completed"}
        for item in [quality_gate, reconcile, latency, freshness, uat]
    )
    return {
        "available": available,
        "message": "Hasil proses tersedia." if available else "Belum ada hasil proses yang tervalidasi.",
        "runtime_config": truth["runtime_config"],
        "control_total": reconcile if reconcile.get("status") == "validated" else None,
        "control_total_proposal": reconcile,
        "quality_gate": {
            "status": quality_gate.get("status"),
            "total_rows": _unwrap(quality_gate.get("total_rows")),
            "valid_rows": _unwrap(quality_gate.get("valid_rows")),
            "rejected_rows": _unwrap(quality_gate.get("rejected_rows")),
            "rejection_rate": _unwrap(quality_gate.get("rejection_rate")),
        },
        "data_quality_score": _unwrap(quality_gate.get("quality_score")),
        "pipeline_latency": _seconds_to_label(_latency_value(latency)),
        "pipeline_latency_raw": latency,
        "data_freshness": "Tersedia" if freshness.get("status") == "validated" else "Belum tersedia",
        "data_freshness_raw": freshness,
        "raw": {
            "truth": truth,
            "qualityGate": quality_gate,
            "reconcile": reconcile,
            "latency": latency,
            "freshness": freshness,
            "rejection": truth["metrics"].get("rejection_rate", {"status": "not_available"}),
            "quality": {"status": quality_gate.get("status"), "data_quality_score": quality_gate.get("quality_score")},
            "uat": uat,
            "uatMatrix": uat.get("matrix"),
            "storageManifest": (truth["storage"].get("manifest") or {}),
            "bab4Evidence": truth["bab4_evidence"],
        },
    }
