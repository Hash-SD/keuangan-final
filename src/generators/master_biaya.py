from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, RAW_DIR, ensure_parent
from src.common.runtime_paths import sample_pdf_path
from src.generators.generate_pdf_audited import load_prodi_data


GOLONGAN_COLUMNS = [f"Gol. {idx}" for idx in range(1, 9)]


def build_master_ukt() -> pd.DataFrame:
    rows = []
    for prodi, payload in load_prodi_data().items():
        for idx, nominal in enumerate(payload["ukts"], start=1):
            rows.append(
                {
                    "fakultas": payload["fakultas"],
                    "prodi": prodi,
                    "golongan_ukt": f"Gol. {idx}",
                    "nominal_ukt": int(nominal),
                }
            )
    return pd.DataFrame(rows)


def build_master_spi() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"fakultas": payload["fakultas"], "prodi": prodi, "nominal_spi": int(payload["spi"])}
            for prodi, payload in load_prodi_data().items()
        ]
    )


def build_ukt_wide(master_ukt: pd.DataFrame | None = None) -> pd.DataFrame:
    master_ukt = master_ukt if master_ukt is not None else build_master_ukt()
    wide = master_ukt.pivot(index=["fakultas", "prodi"], columns="golongan_ukt", values="nominal_ukt").reset_index()
    wide.columns.name = None
    ordered = ["fakultas", "prodi", *GOLONGAN_COLUMNS]
    wide = wide[ordered].sort_values(["fakultas", "prodi"]).reset_index(drop=True)
    wide.insert(0, "No", range(1, len(wide) + 1))
    return wide.rename(columns={"fakultas": "Fakultas", "prodi": "Prodi"})


def build_dummy_mahasiswa(seed_count: int = 410) -> pd.DataFrame:
    master_ukt = build_master_ukt()
    master_spi = build_master_spi().set_index("prodi")
    rows = []
    prodis = list(load_prodi_data().keys())
    for idx in range(1, seed_count + 1):
        prodi = prodis[(idx - 1) % len(prodis)]
        golongan_number = ((idx - 1) % 8) + 1
        golongan = f"Gol. {golongan_number}"
        biaya = master_ukt[(master_ukt["prodi"] == prodi) & (master_ukt["golongan_ukt"] == golongan)].iloc[0]
        rows.append(
            {
                "nim_dummy": f"DUMMY2024{idx:04d}",
                "nama_dummy": f"Mahasiswa Dummy {idx:03d}",
                "fakultas": biaya["fakultas"],
                "prodi": prodi,
                "angkatan": 2024 - ((idx - 1) % 4),
                "semester": ((idx - 1) % 8) + 1,
                "golongan_ukt": golongan,
                "nominal_ukt": int(biaya["nominal_ukt"]),
                "nominal_spi": int(master_spi.loc[prodi, "nominal_spi"]),
                "status_mahasiswa": ["Aktif", "Cuti", "Lulus"][(idx - 1) % 3],
            }
        )
    return pd.DataFrame(rows)


def write_master_biaya() -> list[Path]:
    master_ukt = build_master_ukt()
    master_spi = build_master_spi()
    mahasiswa = build_dummy_mahasiswa()
    ukt_path = GENERATED_DIR / "master_ukt_itera.csv"
    spi_path = GENERATED_DIR / "master_spi_itera.csv"
    mahasiswa_path = GENERATED_DIR / "dummy_mahasiswa_itera.csv"
    excel_path = RAW_DIR / "excel" / "master_biaya_itera.xlsx"
    for path in [ukt_path, spi_path, mahasiswa_path, excel_path]:
        ensure_parent(path)
    master_ukt.to_csv(ukt_path, index=False)
    master_spi.to_csv(spi_path, index=False)
    mahasiswa.to_csv(mahasiswa_path, index=False)
    metadata = pd.DataFrame(
        [
            {"key": "source_type", "value": "dummy_reference"},
            {"key": "source_pdf", "value": sample_pdf_path().as_posix()},
            {"key": "generated_for", "value": "Portal Keuangan"},
            {"key": "contains_real_personal_data", "value": "false"},
        ]
    )
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        build_ukt_wide(master_ukt).to_excel(writer, sheet_name="UKT_Wide", index=False)
        master_ukt.to_excel(writer, sheet_name="UKT_Long", index=False)
        master_spi.to_excel(writer, sheet_name="SPI", index=False)
        metadata.to_excel(writer, sheet_name="Metadata", index=False)
    return [ukt_path, spi_path, mahasiswa_path, excel_path]


if __name__ == "__main__":
    for output in write_master_biaya():
        print(output)
