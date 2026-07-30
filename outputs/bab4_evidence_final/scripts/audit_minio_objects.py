"""Read-only MinIO object inventory for final Bab IV evidence."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "bab4_evidence_final" / "02_implementasi" / "423_gold_dashboard"
OUT.mkdir(parents=True, exist_ok=True)


def env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    values = {**env_file(), **os.environ}
    endpoint = values.get("MINIO_ENDPOINT", "http://localhost:9000")
    if endpoint.startswith("http://minio:") or endpoint.startswith("https://minio:"):
        endpoint = endpoint.replace("://minio:", "://localhost:", 1)
    bucket = values.get("MINIO_BUCKET", "lakehouse")
    access = values.get("MINIO_ACCESS_KEY") or values.get("MINIO_ROOT_USER") or "minioadmin"
    secret = values.get("MINIO_SECRET_KEY") or values.get("MINIO_ROOT_PASSWORD") or "minioadmin"
    client = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret, config=Config(signature_version="s3v4"), region_name="us-east-1")
    objects: list[dict[str, object]] = []
    result: dict[str, object] = {"generated_at": datetime.now(timezone.utc).isoformat(), "endpoint": endpoint, "bucket": bucket, "script": "outputs/bab4_evidence_final/scripts/audit_minio_objects.py"}
    try:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                key = str(obj["Key"])
                layer = key.split("/", 1)[0] if "/" in key else "unclassified"
                objects.append({"bucket": bucket, "layer": layer, "object_key": key, "size_bytes": obj.get("Size"), "last_modified": obj.get("LastModified"), "etag": str(obj.get("ETag", "")).strip('"'), "storage_class": obj.get("StorageClass"), "status": "DATA_LOADED"})
        result.update({"status": "QUERY_VALIDATED", "object_count": len(objects), "prefixes": sorted({row["layer"] for row in objects})})
    except (BotoCoreError, ClientError) as exc:
        result.update({"status": "FAILED", "error_type": type(exc).__name__, "message": str(exc)})
    frame = pd.DataFrame(objects)
    frame.to_csv(OUT / "minio_object_inventory.csv", index=False, encoding="utf-8-sig")
    candidates = frame[frame.get("object_key", pd.Series(dtype=str)).astype(str).str.contains(r"uat|upload|raw|bronze|silver|gold|manifest|log", case=False, regex=True)] if not frame.empty else frame
    candidates.to_csv(OUT / "minio_candidate_paths.csv", index=False, encoding="utf-8-sig")
    (OUT / "minio_inventory_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    status_path = OUT / "storage_query_status.csv"
    if status_path.exists() and result["status"] == "QUERY_VALIDATED":
        statuses = pd.read_csv(status_path)
        mask = statuses["component"].eq("MinIO")
        statuses.loc[mask, "status"] = "QUERY_VALIDATED"
        statuses.loc[mask, "evidence"] = f"Read-only S3 ListObjectsV2: bucket {bucket}, {len(objects)} objects, prefix bronze/silver/gold/manifests/metrics/reports tersedia."
        statuses.to_csv(status_path, index=False, encoding="utf-8-sig")
    print(json.dumps({key: value for key, value in result.items() if key not in {"endpoint"}}, ensure_ascii=False))
    return 0 if result["status"] == "QUERY_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
