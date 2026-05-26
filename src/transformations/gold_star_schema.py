from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, ensure_parent
from src.common.time_utils import utc_now_iso


GOLD_DIR = GENERATED_DIR / "gold"


def build_gold() -> dict:
    piutang = pd.read_csv(GENERATED_DIR / "silver" / "fact_piutang_ukt_prodi.csv", dtype={"nim": "string"})
    kualitas = pd.read_csv(GENERATED_DIR / "silver" / "dim_kualitas_piutang.csv")

    dim_organisasi = piutang[["fakultas", "prodi"]].drop_duplicates().reset_index(drop=True)
    dim_organisasi.insert(0, "organisasi_key", range(1, len(dim_organisasi) + 1))
    dim_organisasi["kode_unit"] = dim_organisasi["prodi"].str.upper().str.replace(" ", "_")
    dim_organisasi = dim_organisasi.rename(columns={"fakultas": "nama_fakultas", "prodi": "nama_prodi"})

    dim_mahasiswa = piutang[["nim", "nama_debitur"]].drop_duplicates().reset_index(drop=True)
    dim_mahasiswa.insert(0, "mahasiswa_key", range(1, len(dim_mahasiswa) + 1))

    dim_waktu = piutang[["semester", "tahun_akademik", "umur_tunggakan"]].drop_duplicates().reset_index(drop=True)
    dim_waktu.insert(0, "waktu_tunggakan_key", range(1, len(dim_waktu) + 1))

    fact = piutang.merge(dim_organisasi, left_on=["fakultas", "prodi"], right_on=["nama_fakultas", "nama_prodi"])
    fact = fact.merge(dim_mahasiswa, on=["nim", "nama_debitur"])
    fact = fact.merge(kualitas[["kualitas_piutang_key", "kualitas"]], on="kualitas")
    fact = fact.merge(dim_waktu, on=["semester", "tahun_akademik", "umur_tunggakan"])
    fact = fact[["organisasi_key", "mahasiswa_key", "kualitas_piutang_key", "waktu_tunggakan_key", "nominal_piutang_rp", "source_filename", "batch_id"]]
    fact.insert(0, "piutang_key", range(1, len(fact) + 1))
    fact["jumlah_mhs_penunggak"] = 1
    fact["created_at"] = utc_now_iso()

    ensure_parent(GOLD_DIR / "fact_piutang_ukt_prodi.csv")
    dim_organisasi.to_csv(GOLD_DIR / "dim_organisasi.csv", index=False)
    dim_mahasiswa.to_csv(GOLD_DIR / "dim_mahasiswa.csv", index=False)
    kualitas.to_csv(GOLD_DIR / "dim_kualitas_piutang.csv", index=False)
    dim_waktu.to_csv(GOLD_DIR / "dim_waktu_tunggakan.csv", index=False)
    fact.to_csv(GOLD_DIR / "fact_piutang_ukt_prodi.csv", index=False)
    dashboard = fact.merge(dim_organisasi, on="organisasi_key").merge(dim_mahasiswa, on="mahasiswa_key").merge(kualitas, on="kualitas_piutang_key").merge(dim_waktu, on="waktu_tunggakan_key")
    dashboard.to_csv(GOLD_DIR / "vw_dashboard_piutang_ukt.csv", index=False)
    return {"fact_rows": len(fact), "dashboard_rows": len(dashboard)}


def main() -> None:
    print(build_gold())


if __name__ == "__main__":
    main()

