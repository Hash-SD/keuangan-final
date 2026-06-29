from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR
from src.common.time_utils import utc_now_iso


BUCKET = os.getenv("MINIO_BUCKET", "lakehouse")
UPLOAD_ENABLED = os.getenv("MINIO_UPLOAD_ENABLED", "false").strip().lower() == "true"


LAYERS = {
    "raw": DATA_DIR / "raw",
    "bronze": DATA_DIR / "generated" / "bronze",
    "silver": DATA_DIR / "generated" / "silver",
    "gold": DATA_DIR / "generated" / "gold",
    "reports": OUTPUTS_DIR / "reports",
    "logs": OUTPUTS_DIR / "logs",
}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _row_count(path: Path) -> int | None:
    if path.suffix == ".csv":
        try:
            return max(sum(1 for _ in path.open("r", encoding="utf-8")) - 1, 0)
        except OSError:
            return None
    if path.suffix == ".parquet":
        try:
            import pandas as pd

            return int(len(pd.read_parquet(path, columns=[])))
        except Exception:
            try:
                import pandas as pd

                return int(len(pd.read_parquet(path)))
            except Exception:
                return None
    return None


def _s3_path(layer: str, path: Path) -> str:
    base = LAYERS[layer]
    try:
        suffix = path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        suffix = path.name
    return f"s3://{BUCKET}/{layer}/{suffix}"


def _upload_file(path: Path, layer: str) -> str:
    if not UPLOAD_ENABLED:
        return "mapped_not_uploaded"
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER") or "minioadmin",
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD") or "minioadmin",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
        key = _s3_path(layer, path).split(f"s3://{BUCKET}/", 1)[1]
        client.upload_file(str(path), BUCKET, key)
        return "uploaded"
    except Exception:
        return "failed"


def build_excel_storage_manifest() -> dict[str, Any]:
    run_summary_path = OUTPUTS_DIR / "reports" / "pipeline_run_summary.json"
    run_summary = {}
    if run_summary_path.exists():
        try:
            run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            run_summary = {}
    entries = []
    for layer, root in LAYERS.items():
        files = sorted([path for path in root.rglob("*") if path.is_file()]) if root.exists() else []
        for path in files:
            status = _upload_file(path, layer) if path.suffix.lower() in {".xlsx", ".csv", ".json", ".parquet"} else "skipped"
            entries.append(
                {
                    "layer": layer,
                    "local_path": _rel(path),
                    "s3_path": _s3_path(layer, path),
                    "upload_status": status,
                    "row_count": _row_count(path),
                    "file_size": path.stat().st_size,
                    "created_at": utc_now_iso(),
                    "run_id": run_summary.get("run_id"),
                }
            )
    manifest = {
        "generated_at": utc_now_iso(),
        "bucket": BUCKET,
        "upload_enabled": UPLOAD_ENABLED,
        "required_prefixes": [f"s3://{BUCKET}/{layer}/" for layer in ["raw", "bronze", "silver", "gold", "reports", "logs"]],
        "local_mapping": {layer: _rel(path) for layer, path in LAYERS.items()},
        "run_id": run_summary.get("run_id"),
        "status": "uploaded" if entries and all(item["upload_status"] == "uploaded" for item in entries if item["upload_status"] != "skipped") else "mapped_not_uploaded",
        "entries": entries,
    }
    return manifest


def main() -> None:
    manifest = build_excel_storage_manifest()
    OUTPUTS_DIR.joinpath("reports").mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "reports" / "storage_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print({"status": manifest["status"], "entries": len(manifest["entries"]), "run_id": manifest.get("run_id")})


if __name__ == "__main__":
    main()
