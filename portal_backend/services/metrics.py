from __future__ import annotations

from typing import Any

from src.status.system_truth_status import build_system_truth_status

def _unwrap(item: dict[str, Any] | None) -> Any:
    if not isinstance(item, dict):
        return None
    return item.get("value") if item.get("status") in {"validated", "completed"} else None


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
    quality = truth["metrics"]["data_quality_score"]
    uat = truth["uat"]

    available = any(
        item.get("status") in {"validated", "completed"}
        for item in [quality_gate, reconcile, latency, freshness, quality, uat]
    )
    return {
        "available": available,
        "message": "Hasil proses tersedia." if available else "Belum ada hasil proses yang tervalidasi.",
        "runtime_config": truth["runtime_config"],
        "control_total": {
            "status": reconcile["raw_status"] if reconcile.get("status") == "validated" else reconcile.get("status"),
            "total_piutang": _unwrap(reconcile.get("total_piutang")),
            "jumlah_penunggak": _unwrap(reconcile.get("jumlah_penunggak")),
            "target_total_piutang": _unwrap(reconcile.get("target_total_piutang")),
            "target_jumlah_penunggak": _unwrap(reconcile.get("target_jumlah_penunggak")),
            "source": reconcile.get("source"),
        } if reconcile.get("status") == "validated" else None,
        "control_total_proposal": {
            "expected_total_piutang": _unwrap(reconcile.get("target_total_piutang")),
            "actual_total_piutang": _unwrap(reconcile.get("total_piutang")),
            "expected_penunggak": _unwrap(reconcile.get("target_jumlah_penunggak")),
            "actual_penunggak": _unwrap(reconcile.get("jumlah_penunggak")),
            "status": reconcile.get("status"),
            "source": reconcile.get("source"),
        },
        "quality_gate": {
            "status": quality_gate.get("status"),
            "total_rows": _unwrap(quality_gate.get("total_rows")),
            "valid_rows": _unwrap(quality_gate.get("valid_rows")),
            "rejected_rows": _unwrap(quality_gate.get("rejected_rows")),
            "dropout_rate": _unwrap(quality_gate.get("dropout_rate")),
        },
        "data_quality_score": _unwrap(quality.get("data_quality_score")),
        "pipeline_latency": _seconds_to_label(_unwrap(latency.get("pipeline_latency_seconds")) or _unwrap(latency.get("latency_seconds"))),
        "pipeline_latency_raw": latency,
        "data_freshness": "Tersedia" if freshness.get("status") == "validated" else "Belum tersedia",
        "data_freshness_raw": freshness,
        "raw": {
            "truth": truth,
            "qualityGate": quality_gate,
            "reconcile": reconcile,
            "latency": latency,
            "freshness": freshness,
            "dropout": truth["metrics"]["dropout_rate"],
            "quality": quality,
            "uat": uat,
            "uatMatrix": uat.get("matrix"),
            "storageManifest": (truth["storage"].get("manifest") or {}),
            "bab4Evidence": truth["bab4_evidence"],
        },
    }
