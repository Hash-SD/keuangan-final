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
from src.gold.contract import STAR_DIM_SPEC, STAR_FACT_COLUMNS, STAR_SQL_TYPES

DIM_SQL_TYPES: dict[str, dict[str, str]] = {
    "dim_organisasi": {"org_key": "SERIAL PRIMARY KEY", "prodi": "TEXT NOT NULL", "fakultas": "TEXT"},
    "dim_kegiatan": {"kegiatan_key": "SERIAL PRIMARY KEY", "kegiatan": "TEXT NOT NULL", "cluster_kegiatan": "TEXT", "nomenklatur_path": "TEXT"},
    "dim_akun": {"akun_key": "SERIAL PRIMARY KEY", "akun": "TEXT", "kode_akun": "TEXT", "nama_akun": "TEXT", "nama_akun_asli": "TEXT"},
    "dim_iku": {"iku_key": "SERIAL PRIMARY KEY", "iku": "TEXT", "kode_iku": "TEXT UNIQUE NOT NULL", "nama_iku": "TEXT"},
}


def _star_tables() -> dict[str, list[tuple[str, str]]]:
    tables: dict[str, list[tuple[str, str]]] = {}
    for table, spec in STAR_DIM_SPEC.items():
        tables[table] = [(col, DIM_SQL_TYPES[table].get(col, "TEXT").lower()) for col in [spec["key"]] + spec["natural"]]
    tables["fact_anggaran"] = [(col, STAR_SQL_TYPES.get(col, "TEXT").lower()) for col in STAR_FACT_COLUMNS]
    return tables


TABLES: dict[str, list[tuple[str, str]]] = {
}
for table, columns in _star_tables().items():
    TABLES[table] = columns


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
    stage_schema = "gold_stage_" + _safe_sql_identifier(pipeline_run_id)[:16]
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
    finally:
      conn.close()
    loaded_at = datetime.now(timezone.utc).isoformat()
    _update_manifest(pipeline_run_id, {"postgres_loaded_at": loaded_at, "postgres_row_count": row_count, "postgres_weighted_total": float(weighted_total), "postgres_validation_status": "validated"})
    print("loaded gold tables to postgres")


if __name__ == "__main__":
    main()
