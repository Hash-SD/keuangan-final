from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, ensure_parent
from src.common.logging_utils import write_json
from src.common.runtime_config import configured_batch_id
from src.common.runtime_paths import active_dataset_pointer, active_period_metadata
from src.common.time_utils import utc_now_iso


GOLD_DIR = GENERATED_DIR / "gold"


def _session_id(pointer: dict) -> str:
    return Path(str(pointer.get("session_id") or "dummy")).name or "dummy"


def _previous_dashboard_as_piutang(current_sessions: set[str]) -> pd.DataFrame:
    path = GOLD_DIR / "vw_dashboard_piutang_ukt.csv"
    if not path.exists():
        return pd.DataFrame()
    existing = pd.read_csv(path, dtype={"nim": "string", "dataset_session_id": "string"})
    if "dataset_session_id" not in existing.columns:
        return pd.DataFrame()
    existing["dataset_session_id"] = existing["dataset_session_id"].fillna("").astype(str)
    existing = existing[~existing["dataset_session_id"].isin(current_sessions)]
    if existing.empty:
        return pd.DataFrame()
    renamed = existing.rename(columns={"nama_fakultas": "fakultas", "nama_prodi": "prodi"})
    required = [
        "fakultas",
        "prodi",
        "nim",
        "nama_debitur",
        "semester",
        "tahun_akademik",
        "tahun_anggaran",
        "umur_tunggakan",
        "kualitas",
        "nominal_piutang_rp",
        "source_filename",
        "batch_id",
        "dataset_session_id",
    ]
    for column in required:
        if column not in renamed.columns:
            renamed[column] = None
    return renamed[required]


def _append_previous_gold_if_needed(piutang: pd.DataFrame, pointer: dict) -> pd.DataFrame:
    if "dataset_session_id" not in piutang.columns:
        return piutang
    current_sessions = {str(item) for item in piutang["dataset_session_id"].dropna().unique() if str(item).strip()}
    if len(current_sessions) != 1:
        return piutang
    previous = _previous_dashboard_as_piutang(current_sessions)
    if previous.empty:
        return piutang
    return pd.concat([previous, piutang], ignore_index=True, sort=False)


def build_gold() -> dict:
    pointer = active_dataset_pointer() or {}
    period_metadata = active_period_metadata()
    piutang = pd.read_csv(GENERATED_DIR / "silver" / "fact_piutang_ukt_prodi.csv", dtype={"nim": "string"})
    kualitas = pd.read_csv(GENERATED_DIR / "silver" / "dim_kualitas_piutang.csv")
    if "dataset_session_id" not in piutang.columns:
        piutang["dataset_session_id"] = _session_id(pointer)
    if "tahun_anggaran" not in piutang.columns:
        piutang["tahun_anggaran"] = period_metadata.get("target_tahun_anggaran")
    if "tahun_akademik" not in piutang.columns:
        piutang["tahun_akademik"] = period_metadata.get("target_tahun_akademik")
    if "semester" not in piutang.columns:
        piutang["semester"] = "Tidak diketahui"
    if "batch_id" not in piutang.columns:
        piutang["batch_id"] = configured_batch_id()
    if "source_event" not in piutang.columns:
        piutang["source_event"] = period_metadata.get("source_event")
    piutang["dataset_session_id"] = piutang["dataset_session_id"].fillna(_session_id(pointer)).astype(str)
    piutang["batch_id"] = piutang["batch_id"].fillna(configured_batch_id()).astype(str)
    piutang = _append_previous_gold_if_needed(piutang, pointer)
    piutang["periode_key"] = piutang["tahun_akademik"].astype(str).str.replace("/", "-", regex=False) + "-" + piutang["semester"].astype(str).str.lower()

    dim_organisasi = piutang[["fakultas", "prodi"]].drop_duplicates().reset_index(drop=True)
    dim_organisasi.insert(0, "organisasi_key", range(1, len(dim_organisasi) + 1))
    dim_organisasi["kode_unit"] = dim_organisasi["prodi"].str.upper().str.replace(" ", "_")
    dim_organisasi = dim_organisasi.rename(columns={"fakultas": "nama_fakultas", "prodi": "nama_prodi"})

    dim_mahasiswa = piutang[["nim", "nama_debitur"]].drop_duplicates().reset_index(drop=True)
    dim_mahasiswa.insert(0, "mahasiswa_key", range(1, len(dim_mahasiswa) + 1))

    dim_waktu = piutang[["semester", "tahun_akademik", "tahun_anggaran", "periode_key", "umur_tunggakan"]].drop_duplicates().reset_index(drop=True)
    dim_waktu.insert(0, "waktu_tunggakan_key", range(1, len(dim_waktu) + 1))

    fact = piutang.merge(dim_organisasi, left_on=["fakultas", "prodi"], right_on=["nama_fakultas", "nama_prodi"])
    fact = fact.merge(dim_mahasiswa, on=["nim", "nama_debitur"])
    fact = fact.merge(kualitas[["kualitas_piutang_key", "kualitas"]], on="kualitas")
    fact = fact.merge(dim_waktu, on=["semester", "tahun_akademik", "tahun_anggaran", "periode_key", "umur_tunggakan"])
    fact = fact[[
        "organisasi_key",
        "mahasiswa_key",
        "kualitas_piutang_key",
        "waktu_tunggakan_key",
        "dataset_session_id",
        "tahun_akademik",
        "tahun_anggaran",
        "semester",
        "periode_key",
        "nominal_piutang_rp",
        "source_filename",
        "batch_id",
    ]]
    fact.insert(0, "piutang_key", range(1, len(fact) + 1))
    fact["jumlah_mhs_penunggak"] = 1
    fact["created_at"] = utc_now_iso()

    ensure_parent(GOLD_DIR / "fact_piutang_ukt_prodi.csv")
    session_id = _session_id(pointer)
    session_dir = GOLD_DIR / session_id
    ensure_parent(session_dir / "fact_piutang_ukt_prodi.csv")
    current_fact = fact[fact["dataset_session_id"].astype(str) == session_id] if session_id else fact
    current_dashboard_preview = None
    dim_organisasi.to_csv(GOLD_DIR / "dim_organisasi.csv", index=False)
    dim_mahasiswa.to_csv(GOLD_DIR / "dim_mahasiswa.csv", index=False)
    kualitas.to_csv(GOLD_DIR / "dim_kualitas_piutang.csv", index=False)
    dim_waktu.to_csv(GOLD_DIR / "dim_waktu_tunggakan.csv", index=False)
    fact.to_csv(GOLD_DIR / "fact_piutang_ukt_prodi.csv", index=False)
    pd.read_csv(GENERATED_DIR / "silver" / "silver_master_ukt.csv").to_csv(GOLD_DIR / "dim_biaya_ukt.csv", index=False)
    pd.read_csv(GENERATED_DIR / "silver" / "silver_master_spi.csv").to_csv(GOLD_DIR / "dim_biaya_spi.csv", index=False)
    dashboard = fact.merge(dim_organisasi, on="organisasi_key").merge(dim_mahasiswa, on="mahasiswa_key").merge(kualitas, on="kualitas_piutang_key").merge(dim_waktu, on="waktu_tunggakan_key", suffixes=("", "_dim"))
    for column in ["tahun_akademik", "tahun_anggaran", "semester", "periode_key"]:
        dim_column = f"{column}_dim"
        if column not in dashboard.columns and dim_column in dashboard.columns:
            dashboard[column] = dashboard[dim_column]
    current_dashboard_preview = dashboard[dashboard["dataset_session_id"].astype(str) == session_id] if session_id else dashboard
    current_fact.to_csv(session_dir / "fact_piutang_ukt_prodi.csv", index=False)
    current_dashboard_preview.to_csv(session_dir / "vw_dashboard_piutang_ukt.csv", index=False)
    dashboard.to_csv(GOLD_DIR / "vw_dashboard_piutang_ukt.csv", index=False)
    result = {
        "fact_rows": len(fact),
        "dashboard_rows": len(dashboard),
        "session_fact_rows": len(current_fact),
        "session_dashboard_rows": len(current_dashboard_preview),
        "dataset_mode": pointer.get("dataset_mode", "dummy"),
        "upload_session_id": pointer.get("session_id"),
    }
    write_json(GOLD_DIR / "gold_metadata.json", result)
    return result


def main() -> None:
    print(build_gold())


if __name__ == "__main__":
    main()
