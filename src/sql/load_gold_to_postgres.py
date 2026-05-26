from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR


TABLES = {
    "dim_organisasi": [
        ("organisasi_key", "integer"),
        ("kode_unit", "text"),
        ("nama_fakultas", "text"),
        ("nama_prodi", "text"),
    ],
    "dim_mahasiswa": [
        ("mahasiswa_key", "integer"),
        ("nim", "text"),
        ("nama_debitur", "text"),
    ],
    "dim_kualitas_piutang": [
        ("kualitas_piutang_key", "integer"),
        ("kualitas", "text"),
        ("kriteria", "text"),
        ("persentase_penyisihan", "double precision"),
        ("source_page", "integer"),
    ],
    "dim_waktu_tunggakan": [
        ("waktu_tunggakan_key", "integer"),
        ("semester", "text"),
        ("tahun_akademik", "text"),
        ("umur_tunggakan", "integer"),
    ],
    "fact_piutang_ukt_prodi": [
        ("piutang_key", "bigint"),
        ("organisasi_key", "integer"),
        ("mahasiswa_key", "integer"),
        ("kualitas_piutang_key", "integer"),
        ("waktu_tunggakan_key", "integer"),
        ("nominal_piutang_rp", "bigint"),
        ("source_filename", "text"),
        ("batch_id", "text"),
        ("jumlah_mhs_penunggak", "integer"),
        ("created_at", "timestamptz"),
    ],
    "vw_dashboard_piutang_ukt": [
        ("piutang_key", "bigint"),
        ("organisasi_key", "integer"),
        ("mahasiswa_key", "integer"),
        ("kualitas_piutang_key", "integer"),
        ("waktu_tunggakan_key", "integer"),
        ("nominal_piutang_rp", "bigint"),
        ("source_filename", "text"),
        ("batch_id", "text"),
        ("jumlah_mhs_penunggak", "integer"),
        ("created_at", "timestamptz"),
        ("kode_unit", "text"),
        ("nama_fakultas", "text"),
        ("nama_prodi", "text"),
        ("nim", "text"),
        ("nama_debitur", "text"),
        ("kualitas", "text"),
        ("kriteria", "text"),
        ("persentase_penyisihan", "double precision"),
        ("source_page", "integer"),
        ("semester", "text"),
        ("tahun_akademik", "text"),
        ("umur_tunggakan", "integer"),
    ],
}


def main() -> None:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "metastore"),
        user=os.getenv("POSTGRES_USER", "lakehouse"),
        password=os.getenv("POSTGRES_PASSWORD", "lakehouse"),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS gold")
        for table, columns in TABLES.items():
            cur.execute(f"DROP TABLE IF EXISTS gold.{table}")
            ddl = ", ".join(f"{name} {typ}" for name, typ in columns)
            cur.execute(f"CREATE TABLE gold.{table} ({ddl})")
            csv_path = GENERATED_DIR / "gold" / f"{table}.csv"
            ordered = [name for name, _ in columns]
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    writer.writerow([row.get(column, "") for column in ordered])
            buffer.seek(0)
            copy_sql = f"COPY gold.{table} ({', '.join(ordered)}) FROM STDIN WITH CSV NULL ''"
            cur.copy_expert(copy_sql, buffer)
    conn.close()
    print("loaded gold tables to postgres")


if __name__ == "__main__":
    main()
