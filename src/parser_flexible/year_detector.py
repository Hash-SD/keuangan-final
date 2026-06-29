from __future__ import annotations

from pathlib import Path

from src.excel_ingestion.excel_cell_extractor import detect_year_from_workbook


def detect_year(path: str | Path, tahun_input: str | int | None = None) -> str | None:
    """Detect year from workbook content, then fallback to upload metadata."""
    return detect_year_from_workbook(Path(path), fallback=tahun_input)
