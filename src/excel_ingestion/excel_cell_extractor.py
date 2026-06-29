from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

from src.common.time_utils import utc_now_iso


SUPPORTED_EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xltx", ".xltm"}


@dataclass(frozen=True)
class ExcelSource:
    path: Path
    tahun_input: str | int | None = None
    periode: str | None = None
    prodi: str | None = None
    jenis_dataset: str | None = None

    @property
    def file_id(self) -> str:
        raw = f"{self.path.resolve()}::{self.path.stat().st_mtime_ns if self.path.exists() else ''}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_money(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def cell_fill_color(cell: Cell) -> str | None:
    fill = cell.fill
    if fill is None or fill.fill_type is None:
        return None
    color = fill.fgColor
    if color is None:
        return None
    if color.type == "rgb" and color.rgb:
        return color.rgb.upper()
    if color.type == "theme":
        return f"theme:{color.theme}:{color.tint}"
    if color.type == "indexed":
        return f"indexed:{color.indexed}"
    return None


def dominant_row_color(ws: Worksheet, row_number: int, max_column: int | None = None) -> str | None:
    counts: dict[str, int] = {}
    end_col = min(max_column or ws.max_column, ws.max_column)
    for column_number in range(1, end_col + 1):
        color = cell_fill_color(ws.cell(row=row_number, column=column_number))
        if color:
            counts[color] = counts.get(color, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[0][0]


def row_text(ws: Worksheet, row_number: int, max_column: int | None = None) -> str | None:
    values = []
    end_col = min(max_column or ws.max_column, ws.max_column)
    for column_number in range(1, end_col + 1):
        text = normalize_text(ws.cell(row=row_number, column=column_number).value)
        if text:
            values.append(text)
    return " | ".join(values) if values else None


def merged_range_for(ws: Worksheet, row_number: int, column_number: int) -> str | None:
    for merged in ws.merged_cells.ranges:
        if merged.min_row <= row_number <= merged.max_row and merged.min_col <= column_number <= merged.max_col:
            return str(merged)
    return None


def detect_year_from_workbook(path: Path, fallback: str | int | None = None) -> str | None:
    years: dict[str, int] = {}
    try:
        wb = load_workbook(path, data_only=True, read_only=False)
    except Exception:
        return str(fallback) if fallback else None
    for ws in wb.worksheets:
        max_row = min(ws.max_row, 120)
        max_col = min(ws.max_column, 35)
        for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col):
            for cell in row:
                text = normalize_text(cell.value)
                if not text:
                    continue
                for year in re.findall(r"\b(20[2-4][0-9])\b", text):
                    years[year] = years.get(year, 0) + 1
    wb.close()
    if years:
        return sorted(years.items(), key=lambda item: item[1], reverse=True)[0][0]
    return str(fallback) if fallback else None


def extract_excel_cells(source: ExcelSource, run_id: str) -> pd.DataFrame:
    wb_formula = load_workbook(source.path, data_only=False, read_only=False)
    wb_values = load_workbook(source.path, data_only=True, read_only=False)
    extracted_at = utc_now_iso()
    tahun_detected = detect_year_from_workbook(source.path, source.tahun_input)
    rows: list[dict[str, object]] = []
    for sheet_name in wb_formula.sheetnames:
        ws_formula = wb_formula[sheet_name]
        ws_values = wb_values[sheet_name]
        for row in ws_formula.iter_rows():
            for cell in row:
                value = ws_values.cell(row=cell.row, column=cell.column).value
                formula = cell.value if isinstance(cell.value, str) and cell.value.startswith("=") else None
                fill_color = cell_fill_color(cell)
                merged_range = merged_range_for(ws_formula, cell.row, cell.column)
                if value is None and formula is None and fill_color is None and merged_range is None:
                    continue
                rows.append(
                    {
                        "run_id": run_id,
                        "file_id": source.file_id,
                        "source_file": source.path.name,
                        "source_path": str(source.path),
                        "jenis_dataset": source.jenis_dataset,
                        "tahun_detected": tahun_detected,
                        "tahun_input": source.tahun_input,
                        "periode": source.periode,
                        "prodi": source.prodi,
                        "sheet_name": sheet_name,
                        "row_number": cell.row,
                        "column_number": cell.column,
                        "cell_address": cell.coordinate,
                        "cell_value": value,
                        "cell_formula": formula,
                        "fill_color": fill_color,
                        "is_merged": merged_range is not None,
                        "merged_range": merged_range,
                        "extracted_at": extracted_at,
                    }
                )
    wb_formula.close()
    wb_values.close()
    return pd.DataFrame(rows)


def collect_excel_sources(paths: Iterable[str | Path], **metadata: object) -> list[ExcelSource]:
    sources = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.exists() and path.suffix.lower() in SUPPORTED_EXCEL_SUFFIXES:
            sources.append(
                ExcelSource(
                    path=path,
                    tahun_input=metadata.get("tahun_input"),
                    periode=metadata.get("periode"),
                    prodi=str(metadata.get("prodi") or "") or None,
                    jenis_dataset=str(metadata.get("jenis_dataset") or "") or None,
                )
            )
    return sources
