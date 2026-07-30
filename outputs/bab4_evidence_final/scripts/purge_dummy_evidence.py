"""Targeted removal of confirmed dummy artefacts from local outputs and MinIO."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "bab4_evidence_final" / "00_manifest"
TOKENS = ("dummy-", "batch-dummy", "dummy_transaction_rows", "dummy_invalid_rows")
EXCLUDED_PREFIXES = {
    ROOT / "outputs" / "bab4_evidence_final" / "scripts",
    ROOT / "outputs" / "bab4_evidence_final" / "00_manifest" / "dummy_cleanup_manifest.csv",
}


def env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


def has_dummy_bytes(data: bytes) -> str | None:
    text = data.decode("utf-8", errors="ignore").lower()
    return next((token for token in TOKENS if token in text), None)


def local_targets() -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for path in (ROOT / "outputs").rglob("*"):
        if not path.is_file() or any(str(path).startswith(str(prefix)) for prefix in EXCLUDED_PREFIXES):
            continue
        if path.suffix.lower() not in {".json", ".csv", ".md", ".tex"}:
            continue
        try:
            token = has_dummy_bytes(path.read_bytes())
        except OSError:
            continue
        if token:
            targets.append({"target_type": "local_file", "target": str(path.relative_to(ROOT)), "match_token": token})
    return targets


def minio_targets(client, bucket: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            key = str(obj["Key"])
            if not key.endswith((".json", ".csv", ".md", ".tex")) or obj.get("Size", 0) > 2_000_000:
                continue
            try:
                token = has_dummy_bytes(client.get_object(Bucket=bucket, Key=key)["Body"].read())
            except (BotoCoreError, ClientError):
                continue
            if token:
                targets.append({"target_type": "minio_object", "target": key, "match_token": token})
    return targets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    values = {**env_values(), **os.environ}
    endpoint = values.get("MINIO_ENDPOINT", "http://localhost:9000").replace("://minio:", "://localhost:", 1)
    bucket = values.get("MINIO_BUCKET", "lakehouse")
    client = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1", aws_access_key_id=values.get("MINIO_ACCESS_KEY") or values.get("MINIO_ROOT_USER") or "minioadmin", aws_secret_access_key=values.get("MINIO_SECRET_KEY") or values.get("MINIO_ROOT_PASSWORD") or "minioadmin", config=Config(signature_version="s3v4"))
    targets = local_targets() + minio_targets(client, bucket)
    rows = []
    for target in targets:
        status = "DRY_RUN"
        if args.apply:
            try:
                if target["target_type"] == "local_file":
                    (ROOT / target["target"]).unlink()
                else:
                    client.delete_object(Bucket=bucket, Key=target["target"])
                status = "DELETED"
            except (OSError, BotoCoreError, ClientError) as exc:
                status = f"FAILED:{type(exc).__name__}"
        rows.append({**target, "status": status, "collected_at": datetime.now(timezone.utc).isoformat()})
    OUT.mkdir(parents=True, exist_ok=True)
    target_manifest = OUT / ("dummy_cleanup_manifest.csv" if args.apply else "dummy_cleanup_dry_run.csv")
    columns = ["target_type", "target", "match_token", "status", "collected_at"]
    pd.DataFrame(rows, columns=columns).to_csv(target_manifest, index=False, encoding="utf-8-sig")
    print(json.dumps({"mode": "apply" if args.apply else "dry_run", "targets": len(rows), "deleted": sum(x["status"] == "DELETED" for x in rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
