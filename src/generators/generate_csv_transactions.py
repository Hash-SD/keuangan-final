from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, RAW_DIR, ensure_parent


STATUSES = ["paid", "partial", "unpaid", "failed"]
METHODS = ["VA", "transfer", "loket"]


def _load_piutang_master() -> pd.DataFrame:
    path = GENERATED_DIR / "dummy_piutang_master.csv"
    if not path.exists():
        raise FileNotFoundError("Run generate_pdf_audited.py before generating transactions.")
    return pd.read_csv(path, dtype={"nim": "string"})


def build_transactions(seed: int = 99999999) -> pd.DataFrame:
    rng = random.Random(seed)
    piutang = _load_piutang_master()
    sains_nims = piutang.loc[piutang["prodi"] == "Sains Data", "nim"].tolist()
    all_nims = piutang["nim"].tolist()
    rows = []
    start = datetime(2023, 8, 1)

    for idx in range(800):
        semester = "Ganjil" if idx < 400 else "Genap"
        
        # Pick a random nim
        nim_pool = sains_nims if idx % 17 == 0 else all_nims
        nim = rng.choice(nim_pool)
        
        # Look up their base_ukt from master
        student_data = piutang.loc[piutang["nim"] == nim]
        if not student_data.empty and "base_ukt" in student_data.columns:
            student_row = student_data.iloc[0]
            base_ukt = int(student_row["base_ukt"])
            prodi = str(student_row.get("prodi", "Sains Data"))
            fakultas = str(student_row.get("fakultas", "Fakultas Sains"))
            golongan_ukt = str(student_row.get("golongan_ukt", "Gol. 1"))
            nominal_spi = int(student_row.get("spi", 30_000_000))
        else:
            base_ukt = 2_500_000
            prodi = "Sains Data"
            fakultas = "Fakultas Sains"
            golongan_ukt = "Gol. 1"
            nominal_spi = 30_000_000

        jenis_biaya = "SPI" if idx % 11 == 0 else "UKT"
        nominal_tagihan = nominal_spi if jenis_biaya == "SPI" else base_ukt
        if nominal_tagihan <= 500_000:
            nominal_bayar = nominal_tagihan
        else:
            nominal_bayar = (rng.randint(500_000, nominal_tagihan) // 50000) * 50000

        tanggal = start + timedelta(days=rng.randint(0, 310))
        rows.append(
            {
                "transaction_id": f"TRX-{idx + 1:06d}",
                "nim": nim,
                "nim_dummy": nim,
                "tanggal": tanggal.strftime("%Y-%m-%d"),
                "semester": semester,
                "tahun_akademik": "2023/2024",
                "jenis_biaya": jenis_biaya,
                "prodi": prodi,
                "fakultas": fakultas,
                "golongan_ukt": golongan_ukt,
                "nominal_tagihan": nominal_tagihan,
                "nominal_bayar": nominal_bayar,
                "metode_bayar": rng.choice(METHODS),
                "status_bayar": rng.choice(STATUSES),
                "batch_id": f"BATCH-{semester.upper()}-2026",
                "source_system": "AVITA",
                "created_at": datetime(2026, 5, 26, 10, 0, 0).isoformat(),
            }
        )

    invalid_indices = list(range(0, 16))
    for i, row_idx in enumerate(invalid_indices):
        if i % 4 == 0:
            rows[row_idx]["nim"] = ""
            rows[row_idx]["nim_dummy"] = ""
        elif i % 4 == 1:
            rows[row_idx]["nominal_bayar"] = "bukan_nominal"
        elif i % 4 == 2:
            rows[row_idx]["tanggal"] = "2024-99-99"
        else:
            rows[row_idx]["status_bayar"] = "unknown_status"

    return pd.DataFrame(rows)


def write_transactions(output_dir: Path | None = None) -> list[Path]:
    output_dir = output_dir or (RAW_DIR / "csv")
    df = build_transactions()
    outputs = [
        output_dir / "transaksi_ganjil.csv",
        output_dir / "transaksi_genap.csv",
    ]
    ensure_parent(outputs[0])
    df[df["semester"] == "Ganjil"].to_csv(outputs[0], index=False)
    df[df["semester"] == "Genap"].to_csv(outputs[1], index=False)
    return outputs


if __name__ == "__main__":
    for path in write_transactions():
        print(path)
