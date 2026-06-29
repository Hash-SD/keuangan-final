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
        ("tahun_anggaran", "text"),
        ("periode_key", "text"),
        ("umur_tunggakan", "integer"),
    ],
    "fact_piutang_ukt_prodi": [
        ("piutang_key", "bigint"),
        ("organisasi_key", "integer"),
        ("mahasiswa_key", "integer"),
        ("kualitas_piutang_key", "integer"),
        ("waktu_tunggakan_key", "integer"),
        ("dataset_session_id", "text"),
        ("tahun_akademik", "text"),
        ("tahun_anggaran", "text"),
        ("semester", "text"),
        ("periode_key", "text"),
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
        ("dataset_session_id", "text"),
        ("tahun_akademik", "text"),
        ("tahun_anggaran", "text"),
        ("semester", "text"),
        ("periode_key", "text"),
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
        ("semester_dim", "text"),
        ("tahun_akademik_dim", "text"),
        ("tahun_anggaran_dim", "text"),
        ("periode_key_dim", "text"),
        ("umur_tunggakan", "integer"),
    ],
    "fact_anggaran": [
        ("item_id", "text"),
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
        ("created_at", "timestamptz"),
    ],
    "vw_dashboard_iku_anggaran": [
        ("run_id", "text"),
        ("tahun", "text"),
        ("periode", "text"),
        ("prodi", "text"),
        ("fakultas", "text"),
        ("iku", "text"),
        ("jumlah_weighted_iku", "double precision"),
    ],
    "vw_dashboard_mapping_quality": [
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
        ("created_at", "timestamptz"),
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
            csv_path = GENERATED_DIR / "gold" / f"{table}.csv"
            if not csv_path.exists():
                print(f"skip gold.{table}: {csv_path} not found")
                continue
            cur.execute(f"DROP TABLE IF EXISTS gold.{table}")
            ddl = ", ".join(f"{name} {typ}" for name, typ in columns)
            cur.execute(f"CREATE TABLE gold.{table} ({ddl})")
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
