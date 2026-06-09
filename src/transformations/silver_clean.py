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


def _session_id(pointer: dict) -> str:
    return Path(str(pointer.get("session_id") or "dummy")).name or "dummy"


def _write_session_and_combined(df: pd.DataFrame, filename: str, session_id: str, key: str = "dataset_session_id") -> Path:
    layer_dir = GENERATED_DIR / "silver"
    session_path = layer_dir / session_id / filename
    combined_path = layer_dir / filename
    ensure_parent(session_path)
    ensure_parent(combined_path)

    current = df.copy()
    if key not in current.columns:
        current[key] = session_id
    current[key] = current[key].fillna(session_id).astype(str)
    current.loc[current[key].str.len() == 0, key] = session_id
    current.to_csv(session_path, index=False)

    if combined_path.exists():
        existing = pd.read_csv(combined_path)
        if key in existing.columns:
            existing[key] = existing[key].fillna("").astype(str)
            existing = existing[existing[key] != session_id]
            combined = current if existing.empty else pd.concat([existing, current], ignore_index=True, sort=False)
        else:
            combined = current
    else:
        combined = current
    combined.to_csv(combined_path, index=False)
    return combined_path


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
    session_id = _session_id(pointer)
    period_metadata = active_period_metadata()
    extract_master_control_total()
    dim_kualitas = extract_dim_kualitas_piutang()
    piutang = extract_fact_piutang_ukt_prodi()
    piutang = _apply_period_columns(piutang, pointer, period_metadata)
    piutang["nominal_piutang_rp"] = pd.to_numeric(piutang["nominal_piutang_rp"], errors="coerce").astype("int64")
    piutang["umur_tunggakan"] = pd.to_numeric(piutang["umur_tunggakan"], errors="coerce").astype("int64")
    _write_session_and_combined(piutang, "fact_piutang_ukt_prodi.csv", session_id)

    trx = pd.read_csv(GENERATED_DIR / "bronze" / "csv_transactions_valid.csv", dtype={"nim": "string"})
    trx = _apply_period_columns(trx, pointer, period_metadata)
    _write_session_and_combined(trx, "transactions_clean.csv", session_id)

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
    if rab_path.parent == GENERATED_DIR / "silver":
        _write_session_and_combined(rab_long, rab_path.name, session_id)
    else:
        ensure_parent(rab_path)
        rab_long.to_csv(rab_path, index=False)
    if rab_path.name != "rab_prodi_sains_data_long.csv":
        _write_session_and_combined(rab_long, "rab_prodi_sains_data_long.csv", session_id)
    _write_session_and_combined(rab_long, "silver_rab.csv", session_id)
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
