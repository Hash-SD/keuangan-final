from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, RAW_DIR, ensure_parent
from src.common.time_utils import utc_now_iso


VALID_STATUSES = {"paid", "partial", "unpaid", "failed"}


def validate_transactions() -> dict:
    csv_paths = sorted((RAW_DIR / "csv").glob("transaksi_*.csv"))
    rejected_rows = []
    valid_frames = []
    total_rows = 0
    for csv_path in csv_paths:
        df = pd.read_csv(csv_path, dtype="string")
        total_rows += len(df)
        numeric_nominal = pd.to_numeric(df["nominal_bayar"], errors="coerce")
        valid_date = pd.to_datetime(df["tanggal"], errors="coerce")
        invalid_mask = (
            df["nim"].isna()
            | (df["nim"].str.len() == 0)
            | numeric_nominal.isna()
            | valid_date.isna()
            | ~df["status_bayar"].isin(VALID_STATUSES)
        )
        for row_number, row in df[invalid_mask].iterrows():
            rejected_rows.append(
                {
                    "batch_id": "batch-dummy-20260526",
                    "source_filename": csv_path.name,
                    "row_number": int(row_number) + 2,
                    "error_type": "transaction_validation",
                    "error_message": "NIM, nominal, tanggal, atau status bayar invalid",
                    "created_at": utc_now_iso(),
                }
            )
        clean = df[~invalid_mask].copy()
        clean["nominal_bayar"] = numeric_nominal[~invalid_mask].astype("int64")
        clean["tanggal"] = valid_date[~invalid_mask].dt.strftime("%Y-%m-%d")
        clean["source_filename"] = csv_path.name
        valid_frames.append(clean)
    valid = pd.concat(valid_frames, ignore_index=True) if valid_frames else pd.DataFrame()
    valid_path = DATA_DIR / "generated" / "bronze" / "csv_transactions_valid.csv"
    rejected_path = DATA_DIR / "quarantine" / "logs" / "rejected_rows.csv"
    ensure_parent(valid_path)
    ensure_parent(rejected_path)
    valid.to_csv(valid_path, index=False)
    pd.DataFrame(rejected_rows).to_csv(rejected_path, index=False)
    summary = {
        "batch_id": "batch-dummy-20260526",
        "total_rows": total_rows,
        "valid_rows": len(valid),
        "rejected_rows": len(rejected_rows),
        "dropout_rate": (len(rejected_rows) / total_rows * 100) if total_rows else 0,
        "created_at": utc_now_iso(),
    }
    write_json(DATA_DIR / "quarantine" / "logs" / "quality_gate_summary.json", summary)
    return summary


def main() -> None:
    print(validate_transactions())


if __name__ == "__main__":
    main()

