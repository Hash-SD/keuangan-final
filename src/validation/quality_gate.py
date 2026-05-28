from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, GENERATED_DIR, RAW_DIR, ensure_parent
from src.common.time_utils import utc_now_iso


VALID_STATUSES = {"paid", "partial", "unpaid", "failed"}
VALID_SEMESTERS = {"Ganjil", "Genap"}
VALID_JENIS_BIAYA = {"UKT", "SPI"}
REQUIRED_TRANSACTION_COLUMNS = [
    "transaction_id",
    "nim_dummy",
    "tanggal",
    "semester",
    "tahun_akademik",
    "jenis_biaya",
    "prodi",
    "fakultas",
    "golongan_ukt",
    "nominal_tagihan",
    "nominal_bayar",
    "status_bayar",
    "metode_bayar",
    "batch_id",
]


def _master_maps() -> tuple[dict[tuple[str, str], int], dict[str, tuple[str, int]]]:
    ukt_path = GENERATED_DIR / "master_ukt_itera.csv"
    spi_path = GENERATED_DIR / "master_spi_itera.csv"
    if not ukt_path.exists() or not spi_path.exists():
        from src.generators.master_biaya import write_master_biaya

        write_master_biaya()
    ukt = pd.read_csv(ukt_path, dtype="string")
    spi = pd.read_csv(spi_path, dtype="string")
    ukt["nominal_ukt"] = pd.to_numeric(ukt["nominal_ukt"], errors="coerce").astype("Int64")
    spi["nominal_spi"] = pd.to_numeric(spi["nominal_spi"], errors="coerce").astype("Int64")
    ukt_map = {(row.prodi, row.golongan_ukt): int(row.nominal_ukt) for row in ukt.itertuples(index=False)}
    spi_map = {row.prodi: (row.fakultas, int(row.nominal_spi)) for row in spi.itertuples(index=False)}
    return ukt_map, spi_map


def validate_transactions() -> dict:
    csv_paths = sorted((RAW_DIR / "csv").glob("transaksi_*.csv"))
    ukt_map, spi_map = _master_maps()
    rejected_rows = []
    valid_frames = []
    total_rows = 0
    for csv_path in csv_paths:
        df = pd.read_csv(csv_path, dtype="string")
        total_rows += len(df)
        missing_columns = [column for column in REQUIRED_TRANSACTION_COLUMNS if column not in df.columns]
        if missing_columns:
            raise ValueError(f"Kolom transaksi tidak lengkap pada {csv_path.name}: {', '.join(missing_columns)}")
        numeric_nominal = pd.to_numeric(df["nominal_bayar"], errors="coerce")
        numeric_tagihan = pd.to_numeric(df["nominal_tagihan"], errors="coerce")
        valid_date = pd.to_datetime(df["tanggal"], errors="coerce")
        expected_tagihan = []
        fakultas_matches = []
        for row in df.itertuples(index=False):
            if row.jenis_biaya == "UKT":
                expected = ukt_map.get((row.prodi, row.golongan_ukt))
            elif row.jenis_biaya == "SPI":
                expected = spi_map.get(row.prodi, (None, None))[1]
            else:
                expected = None
            expected_tagihan.append(expected)
            fakultas_matches.append(row.prodi in spi_map and spi_map[row.prodi][0] == row.fakultas)
        expected_tagihan_series = pd.Series(expected_tagihan, index=df.index, dtype="float64")
        invalid_mask = (
            df["transaction_id"].isna()
            | (df["transaction_id"].str.len() == 0)
            | df["nim_dummy"].isna()
            | (df["nim_dummy"].str.len() == 0)
            | numeric_nominal.isna()
            | numeric_tagihan.isna()
            | valid_date.isna()
            | ~df["semester"].isin(VALID_SEMESTERS)
            | ~df["jenis_biaya"].isin(VALID_JENIS_BIAYA)
            | ~df["status_bayar"].isin(VALID_STATUSES)
            | ~pd.Series(fakultas_matches, index=df.index)
            | expected_tagihan_series.isna()
            | (numeric_tagihan != expected_tagihan_series)
        )
        for row_number, row in df[invalid_mask].iterrows():
            rejected_rows.append(
                {
                    "batch_id": "batch-dummy-20260526",
                    "source_filename": csv_path.name,
                    "row_number": int(row_number) + 2,
                    "error_type": "transaction_validation",
                    "error_message": "Transaksi tidak sesuai struktur dummy UKT/SPI atau nilai referensi",
                    "created_at": utc_now_iso(),
                }
            )
        clean = df[~invalid_mask].copy()
        clean["nominal_bayar"] = numeric_nominal[~invalid_mask].astype("int64")
        clean["nominal_tagihan"] = numeric_tagihan[~invalid_mask].astype("int64")
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
