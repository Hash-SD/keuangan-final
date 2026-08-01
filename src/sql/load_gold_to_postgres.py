from __future__ import annotations

import csv
import io
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, OUTPUTS_DIR


TABLES = {
    "fact_anggaran": [
        ("item_id", "text"),
        ("dataset_session_id", "text"),
        ("run_id", "text"),
        ("tahun", "text"),
        ("periode", "text"),
        ("prodi", "text"),
        ("fakultas", "text"),
        ("kegiatan", "text"),
        ("cluster_kegiatan", "text"),
        ("akun", "text"),
        ("kode_akun", "text"),
        ("nama_akun", "text"),
        ("iku", "text"),
        ("kode_iku", "text"),
        ("nama_iku", "text"),
        ("nomenklatur_path", "text"),
        ("uraian_detail", "text"),
        ("qty", "double precision"),
        ("satuan", "text"),
        ("harga_satuan", "double precision"),
        ("jumlah", "double precision"),
        ("jumlah_weighted_iku", "double precision"),
        ("allocation_weight", "double precision"),
        ("mapping_status", "text"),
        ("data_quality_flag", "text"),
        ("source_file", "text"),
        ("source_sheet", "text"),
        ("source_row", "integer"),
        ("source_role", "text"),
        ("row_type", "text"),
        ("quality_flags", "text"),
        ("created_at", "timestamptz"),
    ],
    "vw_dashboard_iku_anggaran": [
        ("dataset_session_id", "text"),
        ("run_id", "text"),
        ("tahun", "text"),
        ("periode", "text"),
        ("prodi", "text"),
        ("fakultas", "text"),
        ("iku", "text"),
        ("jumlah_weighted_iku", "double precision"),
    ],
    "vw_dashboard_mapping_quality": [
        ("dataset_session_id", "text"),
        ("run_id", "text"),
        ("mapping_status", "text"),
        ("data_quality_flag", "text"),
        ("item_count", "bigint"),
    ],
    "vw_dashboard_reconciliation": [
        ("source_file", "text"),
        ("total_detail", "double precision"),
        ("total_rekap", "double precision"),
        ("selisih", "double precision"),
        ("validation_status", "text"),
        ("dataset_session_id", "text"),
    ],
    "vw_dashboard_detail_item": [
        ("item_id", "text"),
        ("dataset_session_id", "text"),
        ("run_id", "text"),
        ("tahun", "text"),
        ("periode", "text"),
        ("prodi", "text"),
        ("fakultas", "text"),
        ("kegiatan", "text"),
        ("cluster_kegiatan", "text"),
        ("akun", "text"),
        ("kode_akun", "text"),
        ("nama_akun", "text"),
        ("iku", "text"),
        ("kode_iku", "text"),
        ("nama_iku", "text"),
        ("nomenklatur_path", "text"),
        ("uraian_detail", "text"),
        ("qty", "double precision"),
        ("satuan", "text"),
        ("harga_satuan", "double precision"),
        ("jumlah", "double precision"),
        ("jumlah_weighted_iku", "double precision"),
        ("allocation_weight", "double precision"),
        ("mapping_status", "text"),
        ("data_quality_flag", "text"),
        ("source_file", "text"),
        ("source_sheet", "text"),
        ("source_row", "integer"),
        ("source_role", "text"),
        ("row_type", "text"),
        ("quality_flags", "text"),
        ("created_at", "timestamptz"),
    ],
}


def _active_run_outputs(pipeline_run_id: str, dataset_session_id: str) -> dict[str, dict[str, str]]:
    pointer_path = OUTPUTS_DIR / "reports" / "active_gold_run.json"
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gold aktif belum tersedia untuk publish PostgreSQL.") from exc
    if pointer.get("dataset_session_id") != dataset_session_id or pointer.get("pipeline_run_id") != pipeline_run_id:
        raise RuntimeError("Identitas Gold aktif tidak cocok dengan request PostgreSQL.")
    if pointer.get("status") != "PUBLISHED":
        raise RuntimeError("Gold aktif belum berstatus PUBLISHED.")
    return pointer.get("outputs") or {}


def _safe_sql_identifier(value: str) -> str:
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch == "_")
    if not cleaned or cleaned != value.replace("-", ""):
        raise ValueError("SQL identifier tidak valid")
    return cleaned


def _update_manifest(pipeline_run_id: str, updates: dict[str, object]) -> None:
    manifest_path = OUTPUTS_DIR / "reports" / "pipeline_runs" / f"{pipeline_run_id}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"pipeline_run_id": pipeline_run_id}
    manifest.update(updates)
    temporary = manifest_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(manifest_path)


def main() -> None:
    pipeline_run_id = os.getenv("PIPELINE_RUN_ID")
    dataset_session_id = os.getenv("DATASET_SESSION_ID")
    if not pipeline_run_id or not dataset_session_id:
        raise RuntimeError("PIPELINE_RUN_ID dan DATASET_SESSION_ID wajib untuk publish PostgreSQL.")
    outputs = _active_run_outputs(pipeline_run_id, dataset_session_id)
    load_started_at = datetime.now(timezone.utc).isoformat()
    _update_manifest(pipeline_run_id, {"postgres_load_started_at": load_started_at})
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "metastore"),
        user=os.getenv("POSTGRES_USER", "lakehouse"),
        password=os.getenv("POSTGRES_PASSWORD", "lakehouse"),
    )
    conn.autocommit = False
    stage_schema = f"gold_stage_{pipeline_run_id.replace('-', '')[:16]}"
    try:
      with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS gold")
        cur.execute(f"DROP SCHEMA IF EXISTS {stage_schema} CASCADE")
        cur.execute(f"CREATE SCHEMA {stage_schema}")
        for table, columns in TABLES.items():
            csv_path = Path(str((outputs.get(f"{table}.csv") or {}).get("csv") or ""))
            if not csv_path.exists():
                raise RuntimeError(f"Output Gold wajib tidak ditemukan: {table}")
            ddl = ", ".join(f"{name} {typ}" for name, typ in columns)
            cur.execute(f"CREATE TABLE {stage_schema}.{table} ({ddl})")
            ordered = [name for name, _ in columns]
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    writer.writerow([row.get(column, "") for column in ordered])
            buffer.seek(0)
            copy_sql = f"COPY {stage_schema}.{table} ({', '.join(ordered)}) FROM STDIN WITH CSV NULL ''"
            cur.copy_expert(copy_sql, buffer)
        cur.execute(f"SELECT COUNT(*), COALESCE(SUM(jumlah_weighted_iku), 0) FROM {stage_schema}.fact_anggaran WHERE dataset_session_id=%s AND run_id=%s", (dataset_session_id, pipeline_run_id))
        row_count, weighted_total = cur.fetchone()
        if row_count == 0:
            raise RuntimeError("Staging PostgreSQL kosong untuk dataset/run aktif.")
        for table in TABLES:
            cur.execute(f"DROP TABLE IF EXISTS gold.{table} CASCADE")
            cur.execute(f"ALTER TABLE {stage_schema}.{table} SET SCHEMA gold")
        cur.execute(f"DROP SCHEMA {stage_schema}")
      conn.commit()
    except Exception:
      conn.rollback()
      _update_manifest(pipeline_run_id, {"postgres_validation_status": "failed"})
      raise
    conn.close()
    loaded_at = datetime.now(timezone.utc).isoformat()
    _update_manifest(pipeline_run_id, {"postgres_loaded_at": loaded_at, "postgres_row_count": row_count, "postgres_weighted_total": float(weighted_total), "postgres_validation_status": "validated"})
    print("loaded gold tables to postgres")


if __name__ == "__main__":
    main()
