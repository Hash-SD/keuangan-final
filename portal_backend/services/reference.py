from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .files import relative_path
from .paths import PDF_SAMPLE_PATH, RAW_CSV_DIR, RAW_EXCEL_RAB_PATH, RAW_PDF_PATH


CSV_REQUIRED_COLUMNS = {
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
}


def _csv_file_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"filename": path.name, "status": "missing", "rows": 0, "missing_columns": sorted(CSV_REQUIRED_COLUMNS)}
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            rows = sum(1 for _ in reader)
        missing = sorted(CSV_REQUIRED_COLUMNS - columns)
        return {
            "filename": path.name,
            "status": "ready" if not missing else "needs_review",
            "path": relative_path(path),
            "rows": rows,
            "missing_columns": missing,
        }
    except OSError as exc:
        return {"filename": path.name, "status": "error", "rows": 0, "message": str(exc)}


def pdf_sample_status() -> dict[str, Any]:
    if not PDF_SAMPLE_PATH.exists():
        return {
            "available": False,
            "message": "PDF audited belum ditemukan. Letakkan file di data/samples/ITERA_LKTA2024Audited.pdf",
            "ocr_required": False,
            "method": "programmatic_text_extraction",
        }
    return {
        "available": True,
        "path": relative_path(PDF_SAMPLE_PATH),
        "raw_pdf_available": RAW_PDF_PATH.exists(),
        "raw_path": relative_path(RAW_PDF_PATH),
        "method": "programmatic_text_extraction",
        "ocr_required": False,
    }


def excel_rab_status() -> dict[str, Any]:
    if not RAW_EXCEL_RAB_PATH.exists():
        return {
            "status": "missing",
            "path": relative_path(RAW_EXCEL_RAB_PATH),
            "sheet": "RAB",
            "total_pagu_expected": 150_000_000,
        }
    try:
        workbook = load_workbook(RAW_EXCEL_RAB_PATH, read_only=True, data_only=True)
        sheet_name = "RAB" if "RAB" in workbook.sheetnames else workbook.sheetnames[0]
        worksheet = workbook[sheet_name]
        header = [str(cell.value).strip() if cell.value is not None else "" for cell in next(worksheet.iter_rows(min_row=1, max_row=1))]
        required_minimal = {"kode_akun", "nama_kegiatan"}
        has_month_columns = any(column.lower() in {"januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember", "bulan"} for column in header)
        missing = sorted(required_minimal - {column.lower() for column in header})
        return {
            "status": "ready" if not missing and has_month_columns else "needs_review",
            "path": relative_path(RAW_EXCEL_RAB_PATH),
            "sheet": sheet_name,
            "columns": header,
            "missing_columns": missing,
            "wide_format_detected": has_month_columns,
            "silver_unpivot_target": "data/generated/silver/rab_prodi_sains_data_long.csv",
            "total_pagu_expected": 150_000_000,
        }
    except (OSError, StopIteration) as exc:
        return {"status": "error", "path": relative_path(RAW_EXCEL_RAB_PATH), "message": str(exc)}


def source_status() -> dict[str, Any]:
    csv_files = sorted(path for path in RAW_CSV_DIR.glob("transaksi_*.csv") if path.is_file())
    csv_statuses = [_csv_file_status(path) for path in csv_files]
    total_csv_rows = sum(item.get("rows", 0) for item in csv_statuses)
    return {
        "pdf": pdf_sample_status(),
        "csv": {
            "status": "ready" if len(csv_statuses) >= 2 and total_csv_rows >= 800 else "needs_review",
            "expected_files": 2,
            "files": csv_statuses,
            "total_rows": total_csv_rows,
            "target_rows": 800,
        },
        "excel": excel_rab_status(),
        "control_totals": {
            "total_piutang_ukt_sains_data": 31_250_000,
            "jumlah_mahasiswa_penunggak_sains_data": 15,
            "total_pagu_rab": 150_000_000,
            "csv_rows": 800,
        },
    }
