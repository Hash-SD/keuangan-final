from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import DATA_DIR, GENERATED_DIR, RAW_DIR, ensure_parent
from src.common.logging_utils import write_json
from src.common.runtime_paths import active_dataset_pointer, active_period_metadata, raw_rab_path, silver_rab_path
from src.extraction.extract_pdf_piutang import extract_dim_kualitas_piutang, extract_fact_piutang_ukt_prodi, extract_master_control_total
from src.generators.generate_excel_rab import MONTHS


def _apply_period_columns(df: pd.DataFrame, pointer: dict, metadata: dict[str, str]) -> pd.DataFrame:
    result = df.copy()
    if "dataset_session_id" not in result.columns or result["dataset_session_id"].isna().all():
        result["dataset_session_id"] = pointer.get("session_id") or "dummy"
    if "tahun_akademik" not in result.columns or result["tahun_akademik"].isna().all():
        result["tahun_akademik"] = metadata.get("target_tahun_akademik")
    if "tahun_anggaran" not in result.columns or result["tahun_anggaran"].isna().all():
        result["tahun_anggaran"] = metadata.get("target_tahun_anggaran")
    if "semester" not in result.columns:
        result["semester"] = "Tidak diketahui"
    if "source_file" not in result.columns:
        result["source_file"] = result.get("source_filename", "unknown")
    if "source_event" not in result.columns:
        result["source_event"] = metadata.get("source_event")
    return result


def clean_silver() -> dict:
    pointer = active_dataset_pointer() or {}
    period_metadata = active_period_metadata()
    extract_master_control_total()
    dim_kualitas = extract_dim_kualitas_piutang()
    piutang = extract_fact_piutang_ukt_prodi()
    piutang = _apply_period_columns(piutang, pointer, period_metadata)
    piutang["nominal_piutang_rp"] = pd.to_numeric(piutang["nominal_piutang_rp"], errors="coerce").astype("int64")
    piutang["umur_tunggakan"] = pd.to_numeric(piutang["umur_tunggakan"], errors="coerce").astype("int64")
    piutang_path = GENERATED_DIR / "silver" / "fact_piutang_ukt_prodi.csv"
    ensure_parent(piutang_path)
    piutang.to_csv(piutang_path, index=False)

    trx = pd.read_csv(GENERATED_DIR / "bronze" / "csv_transactions_valid.csv", dtype={"nim": "string"})
    trx = _apply_period_columns(trx, pointer, period_metadata)
    trx_path = GENERATED_DIR / "silver" / "transactions_clean.csv"
    ensure_parent(trx_path)
    trx.to_csv(trx_path, index=False)

    master_ukt = pd.read_csv(GENERATED_DIR / "master_ukt_itera.csv")
    master_spi = pd.read_csv(GENERATED_DIR / "master_spi_itera.csv")
    mahasiswa = pd.read_csv(GENERATED_DIR / "dummy_mahasiswa_itera.csv", dtype={"nim_dummy": "string"})
    master_ukt.to_csv(GENERATED_DIR / "silver" / "silver_master_ukt.csv", index=False)
    master_spi.to_csv(GENERATED_DIR / "silver" / "silver_master_spi.csv", index=False)
    mahasiswa.to_csv(GENERATED_DIR / "silver" / "silver_mahasiswa.csv", index=False)

    rab = pd.read_excel(raw_rab_path(), sheet_name="RAB")
    rab_long = rab.melt(
        id_vars=["kode_akun", "nama_kegiatan", "kategori", "total_pagu"],
        value_vars=MONTHS,
        var_name="bulan",
        value_name="alokasi_rp",
    )
    rab_long = _apply_period_columns(rab_long, pointer, period_metadata)
    rab_path = silver_rab_path()
    ensure_parent(rab_path)
    rab_long.to_csv(rab_path, index=False)
    if rab_path.name != "rab_prodi_sains_data_long.csv":
        rab_long.to_csv(GENERATED_DIR / "silver" / "rab_prodi_sains_data_long.csv", index=False)
    rab_long.to_csv(GENERATED_DIR / "silver" / "silver_rab.csv", index=False)
    result = {
        "piutang_rows": len(piutang),
        "kualitas_rows": len(dim_kualitas),
        "transaction_rows": len(trx),
        "rab_rows": len(rab_long),
        "master_ukt_rows": len(master_ukt),
        "master_spi_rows": len(master_spi),
        "dataset_mode": pointer.get("dataset_mode", "dummy"),
        "upload_session_id": pointer.get("session_id"),
    }
    write_json(GENERATED_DIR / "silver" / "silver_metadata.json", result)
    return result


def main() -> None:
    print(clean_silver())


if __name__ == "__main__":
    main()
