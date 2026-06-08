from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .files import csv_preview, relative_path, upload_registry
from .paths import MASTER_BIAYA_EXCEL_PATH, MASTER_SPI_PATH, MASTER_UKT_PATH, PDF_SAMPLE_PATH, RAW_CSV_DIR, RAW_EXCEL_RAB_PATH, RAW_PDF_PATH, SILVER_RAB_PATH
from .runtime_context import read_active_context
from src.common.runtime_paths import active_csv_paths, active_dataset_pointer, raw_pdf_path, raw_rab_path


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
    pointer = active_dataset_pointer()
    if pointer and pointer.get("active_pdf"):
        path = Path(__file__).resolve().parents[2] / pointer["active_pdf"]
        return {
            "available": path.exists(),
            "path": relative_path(path),
            "raw_pdf_available": path.exists(),
            "raw_path": relative_path(path),
            "uploaded_path": pointer["active_pdf"],
            "canonical_path": pointer["active_pdf"],
            "method": "programmatic_text_extraction",
            "ocr_required": False,
            "dataset_mode": "uploaded",
        }
    registry = upload_registry()
    active_pdf = registry.get("active", {}).get("pdf") or {}
    uploaded_pdf_path = None
    if active_pdf.get("path"):
        uploaded_pdf_path = Path(__file__).resolve().parents[2] / active_pdf["path"]
    available_path = (
        uploaded_pdf_path
        if uploaded_pdf_path and uploaded_pdf_path.exists()
        else RAW_PDF_PATH
        if RAW_PDF_PATH.exists()
        else PDF_SAMPLE_PATH
        if PDF_SAMPLE_PATH.exists()
        else None
    )
    if available_path is None:
        return {
            "available": False,
            "message": f"PDF audited belum ditemukan. Letakkan file di {relative_path(RAW_PDF_PATH)}",
            "ocr_required": False,
            "method": "programmatic_text_extraction",
        }
    return {
        "available": True,
        "path": relative_path(available_path),
        "raw_pdf_available": RAW_PDF_PATH.exists(),
        "raw_path": relative_path(RAW_PDF_PATH),
        "uploaded_path": active_pdf.get("path"),
        "canonical_path": active_pdf.get("canonical_path") or (relative_path(RAW_PDF_PATH) if RAW_PDF_PATH.exists() else None),
        "method": "programmatic_text_extraction",
        "ocr_required": False,
    }


def excel_rab_status() -> dict[str, Any]:
    config = read_active_context()
    rab_path = raw_rab_path()
    if not rab_path.exists():
        return {
            "status": "missing",
            "path": relative_path(rab_path),
            "sheet": "RAB",
            "target_prodi": config["target_prodi"],
            "target_tahun_anggaran": config["target_tahun_anggaran"],
            "total_pagu_expected": config["target_total_pagu_rab"],
        }
    try:
        workbook = load_workbook(rab_path, read_only=True, data_only=True)
        sheet_name = "RAB" if "RAB" in workbook.sheetnames else workbook.sheetnames[0]
        worksheet = workbook[sheet_name]
        header = [str(cell.value).strip() if cell.value is not None else "" for cell in next(worksheet.iter_rows(min_row=1, max_row=1))]
        required_minimal = {"kode_akun", "nama_kegiatan"}
        has_month_columns = any(column.lower() in {"januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember", "bulan"} for column in header)
        missing = sorted(required_minimal - {column.lower() for column in header})
        return {
            "status": "ready" if not missing and has_month_columns else "needs_review",
            "path": relative_path(rab_path),
            "sheet": sheet_name,
            "columns": header,
            "missing_columns": missing,
            "wide_format_detected": has_month_columns,
            "silver_unpivot_target": relative_path(SILVER_RAB_PATH),
            "target_prodi": config["target_prodi"],
            "target_tahun_anggaran": config["target_tahun_anggaran"],
            "total_pagu_expected": config["target_total_pagu_rab"],
        }
    except (OSError, StopIteration) as exc:
        return {"status": "error", "path": relative_path(rab_path), "message": str(exc)}


def source_status() -> dict[str, Any]:
    config = read_active_context()
    registry = upload_registry()
    active_csv = registry.get("active", {}).get("csv") or []
    csv_files = []
    for item in active_csv:
        if item.get("path"):
            path = Path(__file__).resolve().parents[2] / item["path"]
            if path.exists():
                csv_files.append(path)
    if not csv_files:
        csv_files = active_csv_paths()
    csv_statuses = [_csv_file_status(path) for path in csv_files]
    total_csv_rows = sum(item.get("rows", 0) for item in csv_statuses)
    target_rows = int(config.get("dummy_transaction_rows") or 0)
    return {
        "pdf": pdf_sample_status(),
        "csv": {
            "status": "ready" if len(csv_statuses) >= 2 and (target_rows == 0 or total_csv_rows >= target_rows) else "needs_review",
            "expected_files": 2,
            "files": csv_statuses,
            "total_rows": total_csv_rows,
            "target_rows": target_rows,
        },
        "excel": excel_rab_status(),
        "control_totals": {
            "target_prodi": config["target_prodi"],
            "target_tahun_akademik": config["target_tahun_akademik"],
            "total_piutang_ukt_target": config.get("target_total_piutang"),
            "jumlah_mahasiswa_penunggak_target": config.get("target_jumlah_penunggak"),
            "total_pagu_rab": config.get("target_total_pagu_rab"),
            "csv_rows": target_rows,
        },
    }


def reference_summary() -> dict[str, Any]:
    ukt_rows = 0
    ukt_program_count = 0
    if MASTER_UKT_PATH.exists():
        try:
            with MASTER_UKT_PATH.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            ukt_rows = len(rows)
            ukt_program_count = len({row["prodi"] for row in rows})
        except OSError:
            pass

    spi_rows = 0
    spi_program_count = 0
    if MASTER_SPI_PATH.exists():
        try:
            with MASTER_SPI_PATH.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            spi_rows = len(rows)
            spi_program_count = len({row["prodi"] for row in rows})
        except OSError:
            pass

    return {
        "ukt": {
            "available": MASTER_UKT_PATH.exists(),
            "path": relative_path(MASTER_UKT_PATH),
            "program_count": ukt_program_count,
            "rows": ukt_rows,
        },
        "spi": {
            "available": MASTER_SPI_PATH.exists(),
            "path": relative_path(MASTER_SPI_PATH),
            "program_count": spi_program_count,
            "rows": spi_rows,
        },
        "pdf_sample": pdf_sample_status(),
        "excel": {
            "master_biaya_available": MASTER_BIAYA_EXCEL_PATH.exists(),
            "master_biaya_path": relative_path(MASTER_BIAYA_EXCEL_PATH),
            "rab_available": RAW_EXCEL_RAB_PATH.exists(),
            "rab_path": relative_path(RAW_EXCEL_RAB_PATH),
        },
    }


def reference_ukt_preview(limit: int = 25) -> dict[str, Any]:
    return csv_preview(MASTER_UKT_PATH, limit=limit)


def reference_spi_preview(limit: int = 25) -> dict[str, Any]:
    return csv_preview(MASTER_SPI_PATH, limit=limit)
