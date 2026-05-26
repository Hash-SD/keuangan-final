from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import RAW_DIR, ensure_parent


MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def build_rab() -> pd.DataFrame:
    activities = [
        ("521001", "Operasional laboratorium data", "Operasional", [3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5]),
        ("521002", "Pengembangan modul praktikum", "Praktikum", [2, 2, 2, 3, 3, 4, 4, 4, 4, 4, 4, 4]),
        ("521003", "Seminar data science", "Seminar", [0, 0, 3, 5, 5, 2, 2, 3, 5, 5, 0, 0]),
        ("521004", "Publikasi mahasiswa dan dosen", "Publikasi", [1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4]),
        ("521005", "Kegiatan akademik prodi", "Akademik", [4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6]),
    ]
    scale = 150_000_000 / sum(sum(a[3]) for a in activities)
    rows = []
    running_total = 0
    for idx, (kode, kegiatan, kategori, weights) in enumerate(activities):
        monthly = [round(w * scale / 1000) * 1000 for w in weights]
        if idx == len(activities) - 1:
            monthly[-1] += 150_000_000 - (running_total + sum(monthly))
        running_total += sum(monthly)
        row = {"kode_akun": kode, "nama_kegiatan": kegiatan, "kategori": kategori}
        row.update(dict(zip(MONTHS, monthly)))
        row["total_pagu"] = sum(monthly)
        rows.append(row)
    return pd.DataFrame(rows)


def write_rab(path: Path | None = None) -> Path:
    path = path or (RAW_DIR / "excel" / "rab_prodi_sains_data.xlsx")
    ensure_parent(path)
    rab = build_rab()
    metadata = pd.DataFrame(
        [
            {"key": "tahun_anggaran", "value": "2024"},
            {"key": "prodi", "value": "Sains Data"},
            {"key": "fakultas", "value": "Fakultas Sains"},
            {"key": "versi_dokumen", "value": "dummy-v1"},
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        rab.to_excel(writer, sheet_name="RAB", index=False)
        metadata.to_excel(writer, sheet_name="metadata", index=False)
    return path


if __name__ == "__main__":
    print(write_rab())
