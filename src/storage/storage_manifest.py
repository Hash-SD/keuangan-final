from __future__ import annotations

import json
import os
import sys
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, GENERATED_DIR, OUTPUTS_DIR, RAW_DIR
from src.common.runtime_config import configured_batch_id, get_runtime_config
from src.common.time_utils import utc_now_iso
from src.status.system_truth_status import build_system_truth_status


@dataclass(frozen=True)
class StorageConfig:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool
    upload_enabled: bool


LAYER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "staging": {"local_path": DATA_DIR / "uploads" / "staging", "prefix": "staging", "ready_when": "exists"},
    "raw": {"local_path": RAW_DIR, "prefix": "raw", "ready_when": "files"},
    "bronze": {"local_path": GENERATED_DIR / "bronze", "prefix": "bronze", "ready_when": "files"},
    "silver": {"local_path": GENERATED_DIR / "silver", "prefix": "silver", "ready_when": "files"},
    "gold": {"local_path": GENERATED_DIR / "gold", "prefix": "gold", "ready_when": "files"},
    "quarantine": {"local_path": DATA_DIR / "quarantine", "prefix": "quarantine", "ready_when": "exists"},
    "manifests": {"local_path": OUTPUTS_DIR / "reports", "prefix": "manifests", "ready_when": "exists"},
    "metrics": {"local_path": OUTPUTS_DIR / "metrics", "prefix": "metrics", "ready_when": "files"},
    "reports": {"local_path": OUTPUTS_DIR / "reports", "prefix": "reports", "ready_when": "exists"},
    "iceberg_warehouse": {"local_path": None, "prefix": "warehouse", "ready_when": "configured"},
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _storage_config() -> StorageConfig:
    return StorageConfig(
        endpoint=os.getenv("MINIO_ENDPOINT", "http://minio:9000").strip() or "http://minio:9000",
        access_key=(
            os.getenv("MINIO_ACCESS_KEY")
            or os.getenv("MINIO_ROOT_USER")
            or os.getenv("AWS_ACCESS_KEY_ID")
            or "minioadmin"
        ),
        secret_key=(
            os.getenv("MINIO_SECRET_KEY")
            or os.getenv("MINIO_ROOT_PASSWORD")
            or os.getenv("AWS_SECRET_ACCESS_KEY")
            or "minioadmin"
        ),
        bucket=os.getenv("MINIO_BUCKET", "lakehouse").strip() or "lakehouse",
        secure=_env_bool("MINIO_SECURE", False),
        upload_enabled=_env_bool("MINIO_UPLOAD_ENABLED", False),
    )


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(__file__).resolve().parents[2]).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_files(path: Path | None) -> list[Path]:
    if path is None or not path.exists():
        return []
    return sorted(item for item in path.rglob("*") if item.is_file())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataset_session_from_relative(relative_to_layer: str) -> str | None:
    first = relative_to_layer.split("/", 1)[0]
    if first.startswith(("upload-", "session-", "dummy-")):
        return first
    return None


def _layer_status(local_path: Path | None, ready_when: str, file_count: int) -> str:
    if ready_when == "configured":
        return "configured"
    if local_path is None or not local_path.exists():
        return "missing"
    if file_count == 0:
        return "empty"
    return "ready"


def _mapping_payload(config: StorageConfig) -> dict[str, Any]:
    layers = {}
    for layer, definition in LAYER_DEFINITIONS.items():
        local_path = definition["local_path"]
        files = _iter_files(local_path)
        layers[layer] = {
            "local_path": _relative(local_path) if local_path is not None else None,
            "s3_prefix": f"s3://{config.bucket}/{definition['prefix']}/",
            "status": _layer_status(local_path, definition["ready_when"], len(files)),
        }
    storage_mode = "minio_upload_enabled" if config.upload_enabled else "local_with_minio_mapping"
    return {
        "batch_id": configured_batch_id(),
        "storage_mode": storage_mode,
        "minio_endpoint": config.endpoint,
        "bucket": config.bucket,
        "layers": layers,
        "generated_at": utc_now_iso(),
    }


def _build_s3_client(config: StorageConfig):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("boto3 belum tersedia; install requirements.txt untuk upload MinIO.") from exc

    return boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        use_ssl=config.secure,
    )


def _ensure_bucket(client: Any, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)


def _upload_files(config: StorageConfig, files_by_layer: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if not config.upload_enabled:
        return {"enabled": False, "status": "skipped", "uploaded_files": 0, "failed_files": 0, "errors": []}

    errors: list[str] = []
    uploaded = 0
    failed = 0
    try:
        client = _build_s3_client(config)
        _ensure_bucket(client, config.bucket)
    except Exception as exc:
        return {"enabled": True, "status": "failed", "uploaded_files": 0, "failed_files": 0, "errors": [str(exc)]}

    for layer, files in files_by_layer.items():
        prefix = LAYER_DEFINITIONS[layer]["prefix"]
        for file_item in files:
            path = Path(file_item["absolute_path"])
            object_key = f"{prefix}/{file_item['relative_to_layer']}"
            try:
                client.upload_file(str(path), config.bucket, object_key)
                uploaded += 1
                file_item["storage_status"] = "uploaded"
                file_item["status"] = "uploaded"
                file_item["s3_uri"] = f"s3://{config.bucket}/{object_key}"
            except Exception as exc:
                failed += 1
                file_item["storage_status"] = "mapped"
                file_item["status"] = "mapped"
                errors.append(f"{object_key}: {exc}")

    return {
        "enabled": True,
        "status": "uploaded" if failed == 0 else "partial",
        "uploaded_files": uploaded,
        "failed_files": failed,
        "errors": errors[:20],
    }


def _manifest_payload(config: StorageConfig, mapping: dict[str, Any]) -> dict[str, Any]:
    files_by_layer: dict[str, list[dict[str, Any]]] = {}
    layer_summaries = {}

    for layer, definition in LAYER_DEFINITIONS.items():
        local_path = definition["local_path"]
        files = _iter_files(local_path)
        file_items = []
        total_size = 0
        for path in files:
            size = path.stat().st_size
            total_size += size
            relative_to_layer = path.relative_to(local_path).as_posix() if local_path else path.name
            object_path = f"{definition['prefix']}/{relative_to_layer}"
            file_items.append(
                {
                    "dataset_session_id": _dataset_session_from_relative(relative_to_layer),
                    "batch_id": configured_batch_id(),
                    "layer": layer,
                    "object_path": object_path,
                    "bucket": config.bucket,
                    "timestamp": utc_now_iso(),
                    "checksum": _sha256(path),
                    "status": "mapped",
                    "path": _relative(path),
                    "absolute_path": str(path.resolve()),
                    "relative_to_layer": relative_to_layer,
                    "size_bytes": size,
                    "storage_status": "mapped",
                    "s3_uri": f"s3://{config.bucket}/{object_path}",
                }
            )
        files_by_layer[layer] = file_items
        layer_summaries[layer] = {
            **mapping["layers"][layer],
            "file_count": len(files),
            "total_size_bytes": total_size,
            "storage_status": "configured" if layer == "iceberg_warehouse" else "mapped",
            "files": file_items,
        }

    upload = _upload_files(config, files_by_layer)
    for layer, files in files_by_layer.items():
        layer_summaries[layer]["files"] = files
        if upload["enabled"] and files:
            statuses = {item["storage_status"] for item in files}
            layer_summaries[layer]["storage_status"] = "uploaded" if statuses == {"uploaded"} else "mapped"

    return {
        "batch_id": configured_batch_id(),
        "generated_at": utc_now_iso(),
        "storage_mode": mapping["storage_mode"],
        "minio_endpoint": config.endpoint,
        "bucket": config.bucket,
        "upload": upload,
        "lineage": _lineage_payload(config, layer_summaries),
        "layers": layer_summaries,
    }


def _lineage_payload(config: StorageConfig, layer_summaries: dict[str, Any]) -> list[dict[str, Any]]:
    transitions = [("staging", "raw"), ("raw", "bronze"), ("bronze", "silver"), ("silver", "gold")]
    lineage = []
    for source, target in transitions:
        source_layer = layer_summaries.get(source, {})
        target_layer = layer_summaries.get(target, {})
        lineage.append(
            {
                "batch_id": configured_batch_id(),
                "from_layer": source,
                "to_layer": target,
                "from_prefix": f"s3://{config.bucket}/{LAYER_DEFINITIONS[source]['prefix']}/",
                "to_prefix": f"s3://{config.bucket}/{LAYER_DEFINITIONS[target]['prefix']}/",
                "from_object_count": source_layer.get("file_count", 0),
                "to_object_count": target_layer.get("file_count", 0),
                "status": "complete"
                if source_layer.get("status") in {"ready", "empty"} and target_layer.get("status") in {"ready", "empty"}
                else "incomplete",
                "timestamp": utc_now_iso(),
            }
        )
    return lineage


def _storage_layers_status(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "validated",
        "bucket": manifest["bucket"],
        "layers": {
            layer: {
                "status": item.get("status"),
                "storage_status": item.get("storage_status"),
                "object_count": item.get("file_count", 0),
                "s3_prefix": item.get("s3_prefix"),
                "sample_objects": [
                    {
                        "object_path": obj.get("object_path"),
                        "checksum": obj.get("checksum"),
                        "status": obj.get("status"),
                    }
                    for obj in item.get("files", [])[:3]
                ],
            }
            for layer, item in manifest["layers"].items()
        },
        "manifest_status": "present",
        "lineage_status": "complete" if all(item["status"] == "complete" for item in manifest["lineage"]) else "incomplete",
        "generated_at": manifest["generated_at"],
    }


def _minio_storage_validation(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": manifest["upload"]["status"] if manifest["upload"]["enabled"] else "mapped",
        "minio_status": manifest["upload"]["status"],
        "bucket": manifest["bucket"],
        "endpoint": manifest["minio_endpoint"],
        "layers": list(manifest["layers"].keys()),
        "object_count_by_layer": {layer: item.get("file_count", 0) for layer, item in manifest["layers"].items()},
        "manifest_status": "present",
        "lineage_status": "complete" if all(item["status"] == "complete" for item in manifest["lineage"]) else "incomplete",
        "object_sample_by_layer": {
            layer: [obj.get("object_path") for obj in item.get("files", [])[:3]]
            for layer, item in manifest["layers"].items()
        },
        "generated_at": manifest["generated_at"],
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def _uat_category(score: float) -> str:
    if score >= 4.21:
        return "Sangat baik"
    if score >= 3.41:
        return "Baik"
    if score >= 2.61:
        return "Cukup"
    if score >= 1.81:
        return "Kurang"
    return "Sangat kurang"


def _evidence_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    config = get_runtime_config()
    reconcile = _read_json(OUTPUTS_DIR / "metrics" / "reconcile_control_total.json") or {}
    quality_gate = _read_json(DATA_DIR / "quarantine" / "logs" / "quality_gate_summary.json") or {}
    dropout = _read_json(OUTPUTS_DIR / "metrics" / "dropout_rate.json") or quality_gate
    quality = _read_json(OUTPUTS_DIR / "metrics" / "data_quality_score.json") or {}
    uat = _read_json(OUTPUTS_DIR / "uat" / "uat_score_summary.json") or {}
    dashboard = _read_json(OUTPUTS_DIR / "reports" / "superset_dashboard.json") or {}
    uat_average = float(uat.get("average_score", 0) or 0)
    return {
        "batch_id": configured_batch_id(),
        "target_prodi": config.target_prodi,
        "target_tahun_akademik": config.target_tahun_akademik,
        "total_piutang_target_prodi": reconcile.get("total_piutang"),
        "jumlah_penunggak_target_prodi": reconcile.get("jumlah_penunggak"),
        "total_rows_transaksi": quality_gate.get("total_rows") or dropout.get("total_rows"),
        "valid_rows": quality_gate.get("valid_rows") or dropout.get("valid_rows"),
        "rejected_rows": quality_gate.get("rejected_rows") or dropout.get("rejected_rows"),
        "dropout_rate": dropout.get("dropout_rate"),
        "data_quality_score": quality.get("data_quality_score"),
        "storage_layer_status": {
            layer: {
                "status": payload.get("status"),
                "storage_status": payload.get("storage_status"),
                "file_count": payload.get("file_count"),
                "s3_prefix": payload.get("s3_prefix"),
            }
            for layer, payload in manifest["layers"].items()
        },
        "uat_average": round(uat_average, 2),
        "uat_percentage": uat.get("percentage", round(uat_average / 5 * 100, 2) if uat_average else None),
        "uat_category": uat.get("category") or (_uat_category(uat_average) if uat_average else None),
        "dashboard_url": dashboard.get("dashboard_url", "http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/"),
        "executed_at": utc_now_iso(),
    }


def generate_storage_manifest() -> dict[str, Any]:
    config = _storage_config()
    mapping = _mapping_payload(config)
    manifest = _manifest_payload(config, mapping)
    write_json(OUTPUTS_DIR / "reports" / "storage_mapping.json", mapping)
    write_json(OUTPUTS_DIR / "reports" / "storage_manifest.json", manifest)
    write_json(OUTPUTS_DIR / "reports" / "storage_layers_status.json", _storage_layers_status(manifest))
    write_json(OUTPUTS_DIR / "reports" / "minio_storage_validation.json", _minio_storage_validation(manifest))
    write_json(OUTPUTS_DIR / "reports" / "bab4_evidence_summary.json", _evidence_summary(manifest))
    build_system_truth_status(write_outputs=True)
    return manifest


def main() -> None:
    manifest = generate_storage_manifest()
    print(
        {
            "batch_id": manifest["batch_id"],
            "storage_mode": manifest["storage_mode"],
            "upload_status": manifest["upload"]["status"],
            "layers": {name: item["status"] for name, item in manifest["layers"].items()},
        }
    )


if __name__ == "__main__":
    main()
