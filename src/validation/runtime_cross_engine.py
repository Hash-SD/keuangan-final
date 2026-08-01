from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import OUTPUTS_DIR


def _query_postgres(dataset_session_id: str, pipeline_run_id: str) -> dict[str, object]:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres-metastore"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "metastore"),
        user=os.getenv("POSTGRES_USER", "lakehouse"),
        password=os.getenv("POSTGRES_PASSWORD", "lakehouse"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), COUNT(DISTINCT item_id), COALESCE(SUM(jumlah_weighted_iku), 0) "
                "FROM gold.fact_anggaran WHERE dataset_session_id=%s AND run_id=%s",
                (dataset_session_id, pipeline_run_id),
            )
            row_count, unique_items, weighted_total = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM gold.fact_anggaran")
            all_rows = cur.fetchone()[0]
        return {"status": "validated", "row_count": row_count, "unique_items": unique_items, "weighted_total": float(weighted_total), "all_rows": all_rows}
    finally:
        conn.close()


def _query_trino(dataset_session_id: str, pipeline_run_id: str) -> dict[str, object]:
    query = (
        "SELECT COUNT(*) AS row_count, COUNT(DISTINCT item_id) AS unique_items, "
        "COALESCE(SUM(jumlah_weighted_iku), 0) AS weighted_total "
        "FROM postgres.gold.fact_anggaran "
        f"WHERE dataset_session_id = '{dataset_session_id.replace(chr(39), chr(39) * 2)}' "
        f"AND run_id = '{pipeline_run_id.replace(chr(39), chr(39) * 2)}'"
    )
    request = Request(
        os.getenv("TRINO_URL", "http://trino:8080/v1/statement"),
        data=query.encode("utf-8"),
        headers={"X-Trino-User": "airflow", "X-Trino-Catalog": "postgres", "X-Trino-Schema": "gold", "Content-Type": "text/plain"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(payload["error"].get("message") or "Trino query failed")
    rows = payload.get("data") or []
    next_uri = payload.get("nextUri")
    while not rows and next_uri:
        with urlopen(Request(next_uri, headers={"X-Trino-User": "airflow"}), timeout=30) as response:
            page = json.loads(response.read().decode("utf-8"))
        if page.get("error"):
            raise RuntimeError(page["error"].get("message") or "Trino query failed")
        rows = page.get("data") or []
        next_uri = page.get("nextUri")
    if not rows:
        raise RuntimeError("Trino query tidak mengembalikan data")
    row_count, unique_items, weighted_total = rows[0]
    return {"status": "validated", "row_count": int(row_count), "unique_items": int(unique_items), "weighted_total": float(weighted_total)}


def main() -> None:
    dataset_session_id = os.environ.get("DATASET_SESSION_ID")
    pipeline_run_id = os.environ.get("PIPELINE_RUN_ID")
    if not dataset_session_id or not pipeline_run_id:
        raise RuntimeError("DATASET_SESSION_ID dan PIPELINE_RUN_ID wajib untuk validasi cross-engine.")
    postgres = _query_postgres(dataset_session_id, pipeline_run_id)
    trino = _query_trino(dataset_session_id, pipeline_run_id)
    difference = abs(postgres["weighted_total"] - trino["weighted_total"])
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_session_id": dataset_session_id,
        "pipeline_run_id": pipeline_run_id,
        "postgres": postgres,
        "trino": trino,
        "weighted_total_difference": difference,
        "status": "PASS" if postgres["row_count"] == trino["row_count"] and postgres["unique_items"] == trino["unique_items"] and difference < 1 else "FAIL",
    }
    path = OUTPUTS_DIR / "reports" / "pipeline_runs" / f"{pipeline_run_id}.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    manifest["trino_postgres_validation"] = result
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUTS_DIR / "reports" / "trino_postgres_catalog_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if result["status"] != "PASS":
        raise RuntimeError(f"Cross-engine validation failed: {json.dumps(result)}")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
