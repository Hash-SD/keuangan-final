from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, OUTPUTS_DIR
from src.generators.generate_csv_transactions import write_transactions
from src.generators.generate_excel_rab import write_rab
from src.generators.generate_pdf_audited import write_pdf
from src.generators.master_biaya import write_master_biaya


def _set_env(args: argparse.Namespace) -> None:
    if args.tahun_akademik:
        os.environ["PORTAL_TARGET_TAHUN_AKADEMIK"] = args.tahun_akademik
    if args.tahun_anggaran:
        os.environ["PORTAL_TARGET_TAHUN_ANGGARAN"] = args.tahun_anggaran
    if args.dataset_session_id:
        os.environ["PORTAL_BATCH_ID"] = args.dataset_session_id
    if args.seed is not None:
        os.environ["PORTAL_DUMMY_SEED"] = str(args.seed)
    if args.target_total_piutang is not None:
        os.environ["PORTAL_TARGET_TOTAL_PIUTANG"] = str(args.target_total_piutang)
    if args.target_jumlah_penunggak is not None:
        os.environ["PORTAL_TARGET_JUMLAH_PENUNGGAK"] = str(args.target_jumlah_penunggak)


def _summary(dataset_session_id: str, tahun_akademik: str, tahun_anggaran: str, outputs: list[Path]) -> dict:
    csv_paths = [path for path in outputs if path.suffix.lower() == ".csv" and "transaksi_" in path.name]
    excel_paths = [path for path in outputs if path.suffix.lower() == ".xlsx" and "rab" in path.name.lower()]
    pdf_paths = [path for path in outputs if path.suffix.lower() == ".pdf"]
    transaksi = pd.concat([pd.read_csv(path) for path in csv_paths], ignore_index=True) if csv_paths else pd.DataFrame()
    invalid = pd.Series(dtype=bool)
    if not transaksi.empty:
        invalid = (
            transaksi["nim_dummy"].isna()
            | (transaksi["nim_dummy"].astype("string").str.len() == 0)
            | pd.to_numeric(transaksi["nominal_bayar"], errors="coerce").isna()
            | pd.to_datetime(transaksi["tanggal"], errors="coerce").isna()
            | ~transaksi["status_bayar"].isin(["paid", "partial", "unpaid", "failed"])
        )
    piutang_path = DATA_DIR / "generated" / "dummy_piutang_master.csv"
    piutang = pd.read_csv(piutang_path) if piutang_path.exists() else pd.DataFrame()
    rab_total = 0
    if excel_paths:
        rab_total = int(pd.read_excel(excel_paths[0], sheet_name="RAB")["total_pagu"].sum())
    target_piutang = piutang[(piutang.get("prodi") == "Sains Data") & (piutang.get("tahun_akademik") == tahun_akademik)] if not piutang.empty else pd.DataFrame()
    return {
        "dataset_session_id": dataset_session_id,
        "tahun_akademik": tahun_akademik,
        "tahun_anggaran": tahun_anggaran,
        "jumlah_pdf": len(pdf_paths),
        "jumlah_csv": len(csv_paths),
        "jumlah_excel": len(excel_paths),
        "jumlah_transaksi": int(len(transaksi)),
        "jumlah_transaksi_valid_rencana": int((~invalid).sum()) if len(invalid) else 0,
        "jumlah_transaksi_invalid_rencana": int(invalid.sum()) if len(invalid) else 0,
        "jumlah_piutang": int(len(piutang)),
        "total_piutang_target": int(target_piutang["nominal_piutang_rp"].sum()) if not target_piutang.empty else 0,
        "jumlah_penunggak_target": int(len(target_piutang)) if not target_piutang.empty else 0,
        "total_pagu_rab": rab_total,
        "lokasi_file_pdf": [str(path) for path in pdf_paths],
        "lokasi_file_csv": [str(path) for path in csv_paths],
        "lokasi_file_excel": [str(path) for path in excel_paths],
        "status_generator": "success",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tahun-akademik")
    parser.add_argument("--tahun-anggaran")
    parser.add_argument("--dataset-session-id")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--target-total-piutang", type=int)
    parser.add_argument("--target-jumlah-penunggak", type=int)
    args = parser.parse_args()
    _set_env(args)
    dataset_session_id = args.dataset_session_id or os.getenv("PORTAL_BATCH_ID", "dummy")
    tahun_akademik = os.getenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2023/2024")
    tahun_anggaran = os.getenv("PORTAL_TARGET_TAHUN_ANGGARAN", "2024")
    if args.output_root:
        output_root = args.output_root / dataset_session_id
        outputs = [
            *write_master_biaya(),
            write_pdf(output_root / "pdf" / f"laporan_audited_{tahun_anggaran}.pdf"),
            *write_transactions(output_root / "csv"),
            write_rab(output_root / "excel" / f"rab_{tahun_anggaran}.xlsx"),
        ]
    else:
        outputs = [*write_master_biaya(), write_pdf(), *write_transactions(), write_rab()]
    summary = _summary(dataset_session_id, tahun_akademik, tahun_anggaran, outputs)
    reports = OUTPUTS_DIR / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    write_json(reports / f"data_generation_{dataset_session_id}.json", summary)
    for output in outputs:
        print(output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
