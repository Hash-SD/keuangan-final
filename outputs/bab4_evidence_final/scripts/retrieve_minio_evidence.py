"""Retrieve a small, read-only set of MinIO metadata artefacts for Bab IV audit."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "bab4_evidence_final" / "00_manifest" / "minio_evidence"
KEYS = [
    "metrics/data_freshness.json",
    "metrics/pipeline_latency.json",
    "manifests/active_dataset_pointer.json",
    "manifests/active_runtime_context.json",
    "manifests/active_upload_session.json",
    "manifests/latest_upload_metadata.json",
    "manifests/pipeline_run_summary.json",
    "manifests/e2e_pipeline_by_year.json",
    "manifests/e2e_upload_sessions.json",
    "manifests/activity_log.json",
    "manifests/storage_manifest.json",
    "manifests/system_truth_status.json",
    "reports/rab_reconciliation_report.json",
]


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


def main() -> int:
    values = {**read_env(), **os.environ}
    endpoint = values.get("MINIO_ENDPOINT", "http://localhost:9000").replace("://minio:", "://localhost:", 1)
    bucket = values.get("MINIO_BUCKET", "lakehouse")
    client = boto3.client(
        "s3", endpoint_url=endpoint, region_name="us-east-1",
        aws_access_key_id=values.get("MINIO_ACCESS_KEY") or values.get("MINIO_ROOT_USER") or "minioadmin",
        aws_secret_access_key=values.get("MINIO_SECRET_KEY") or values.get("MINIO_ROOT_PASSWORD") or "minioadmin",
        config=Config(signature_version="s3v4"),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, object]] = []
    for key in KEYS:
        try:
            obj = client.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
            target = OUT / key.replace("/", "__")
            target.write_bytes(body)
            index.append({"object_key": key, "local_copy": str(target.relative_to(ROOT)), "size_bytes": len(body), "etag": str(obj.get("ETag", "")).strip('"'), "last_modified": str(obj.get("LastModified")), "sha256": hashlib.sha256(body).hexdigest(), "status": "RETRIEVED"})
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "ClientError")
            index.append({"object_key": key, "status": "NOT_FOUND_OR_UNREADABLE", "reason": code})
        except BotoCoreError as exc:
            index.append({"object_key": key, "status": "FAILED", "reason": type(exc).__name__})
    (OUT / "minio_retrieval_index.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "bucket": bucket, "endpoint_redacted": "configured", "objects": index}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"retrieved": sum(x["status"] == "RETRIEVED" for x in index), "unavailable": sum(x["status"] != "RETRIEVED" for x in index), "output": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
