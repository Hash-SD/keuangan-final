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


def build_transactions(seed: int = 20260526) -> pd.DataFrame:
    rng = random.Random(seed)
    piutang = _load_piutang_master()
    sains_nims = piutang.loc[piutang["prodi"] == "Sains Data", "nim"].tolist()
    all_nims = piutang["nim"].tolist()
    rows = []
    start = datetime(2023, 8, 1)

    for idx in range(800):
        semester = "Ganjil" if idx < 400 else "Genap"
        nim_pool = sains_nims if idx % 17 == 0 else all_nims
        tanggal = start + timedelta(days=rng.randint(0, 310))
        rows.append(
            {
                "transaction_id": f"TRX-{idx + 1:06d}",
                "nim": rng.choice(nim_pool),
                "tanggal": tanggal.strftime("%Y-%m-%d"),
                "semester": semester,
                "tahun_akademik": "2023/2024",
                "nominal_bayar": rng.choice([500000, 750000, 1000000, 1250000, 1500000, 2000000]),
                "metode_bayar": rng.choice(METHODS),
                "status_bayar": rng.choice(STATUSES),
                "source_system": "AVITA",
                "created_at": datetime(2026, 5, 26, 10, 0, 0).isoformat(),
            }
        )

    invalid_indices = list(range(0, 16))
    for i, row_idx in enumerate(invalid_indices):
        if i % 4 == 0:
            rows[row_idx]["nim"] = ""
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
