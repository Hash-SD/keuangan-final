from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "outputs" / "reports" / "cleanup_report.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = ROOT / "outputs" / "archive" / "pre_user_upload_runtime" / stamp
    targets = [
        ROOT / "data" / "raw" / "excel_lakehouse",
        ROOT / "data" / "generated" / "bronze",
        ROOT / "data" / "generated" / "silver",
        ROOT / "data" / "generated" / "gold",
        ROOT / "outputs" / "reports" / "active_excel_lakehouse_dataset.json",
        ROOT / "outputs" / "reports" / "active_gold_run.json",
        ROOT / "outputs" / "reports" / "active_dataset_pointer.json",
    ]
    entries = []
    for target in targets:
        entry = {"path": str(target.relative_to(ROOT)), "exists": target.exists(), "action": "not_present"}
        if target.exists() and args.apply:
            destination = archive / target.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(destination))
            if target.suffix:
                target.parent.mkdir(parents=True, exist_ok=True)
            else:
                target.mkdir(parents=True, exist_ok=True)
                if target == ROOT / "data" / "raw" / "excel_lakehouse":
                    (target / ".gitkeep").touch(exist_ok=True)
            entry.update({"action": "archived_and_cleared", "archive": str(destination.relative_to(ROOT))})
        entries.append(entry)
    report = {
        "status": "CLEAN" if args.apply else "DRY_RUN",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "archive": str(archive.relative_to(ROOT)),
        "entries": entries,
        "database": "NOT_ATTEMPTED",
        "minio": "NOT_ATTEMPTED",
        "superset": "RETAINED_REUSABLE_CONFIGURATION",
    }
    if args.apply:
        try:
            subprocess.run(["docker", "exec", "keuangan-postgres-metastore", "psql", "-v", "ON_ERROR_STOP=1", "-U", "lakehouse", "-d", "metastore", "-c", "DELETE FROM gold.fact_anggaran;"], check=True, capture_output=True, text=True)
            report["database"] = "CLEARED"
        except Exception as exc:
            report["database"] = f"FAILED:{type(exc).__name__}"
        try:
            import boto3
            from botocore.config import Config
            client = boto3.client("s3", endpoint_url="http://localhost:9000", region_name="us-east-1", aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin", config=Config(signature_version="s3v4"))
            keys = [obj["Key"] for page in client.get_paginator("list_objects_v2").paginate(Bucket="lakehouse") for obj in page.get("Contents", []) if obj["Key"].split("/", 1)[0] in {"raw", "bronze", "silver", "gold", "manifests", "metrics", "reports"}]
            for index in range(0, len(keys), 1000):
                client.delete_objects(Bucket="lakehouse", Delete={"Objects": [{"Key": key} for key in keys[index:index + 1000]]})
            report["minio"] = {"status": "CLEARED", "object_count": len(keys)}
        except Exception as exc:
            report["minio"] = f"FAILED:{type(exc).__name__}"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
