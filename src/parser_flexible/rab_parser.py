from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from src.common.detail_amounts import normalize_detail_amount_frame, normalize_detail_amounts
from src.excel_ingestion.excel_cell_extractor import (
    ExcelSource,
    detect_year_from_workbook,
    dominant_row_color,
    normalize_money,
    normalize_text,
    row_text,
)
from src.transformations.budget_cleaning import extract_valid_account


RAB_COLOR_LEVELS = {
    "FFFFFF00": "NOMENKLATUR",
    "FFFF0000": "KEGIATAN",
    "FF00B0F0": "UNIT",
    "FF92D050": "AKUN",
    "FFD8D8D8": "HEADER",
    "FFBFBFBF": "HEADER",
}

QUALITY_OK = "OK"
FORMULA_ERRORS = ("#REF!", "#VALUE!", "#N/A", "#DIV/0!", "#NAME?")


def _stable_id(parts: list[object]) -> str:
    text = "|".join(str(part or "") for part in parts)
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _split_account(text: object) -> tuple[str | None, str | None]:
    return extract_valid_account(normalize_text(text))


def _looks_like_total(text: object) -> bool:
    value = (normalize_text(text) or "").lower()
    first_segment = value.split("|", 1)[0].strip()
    return bool(re.match(r"^(grand\s+total|total|subtotal|jumlah)\b", first_segment))


def _amount_header_score(text: str) -> int:
    if not text:
        return 0
    if "jumah diterima" in text or "jumlah diterima" in text:
        return 0
    if "jumlah total" in text:
        return 100
    if "total setelah pajak" in text:
        return 95
    if "grand total" in text:
        return 90
    if text == "total" or text.endswith(" total") or text.startswith("total "):
        return 85
    if "jumlah usulan" in text or text == "jumlah":
        return 80
    if "nominal" in text:
        return 75
    if "total sebelum pajak" in text:
        return 30
    if "total" in text or "jumlah" in text:
        return 20
    return 0


def _select_amount_column(candidates: list[tuple[int, int]]) -> int | None:
    if not candidates:
        return None
    # Prefer the strongest semantic label, then the right-most matching column.
    return max(candidates, key=lambda item: (item[1], item[0]))[0]


def _parse_iku_from_values(values: list[object]) -> str | None:
    found: list[str] = []
    for value in values:
        text = normalize_text(value)
        if not text:
            continue
        found.extend(re.findall(r"\bIK\s*\d+(?:\.\d+)?\b", text, flags=re.I))
    cleaned = []
    for item in found:
        norm = re.sub(r"\s+", " ", item.upper()).replace("IK ", "IK ")
        if norm not in cleaned:
            cleaned.append(norm)
    return "; ".join(cleaned) if cleaned else None


def _quality_flag(row: dict[str, object]) -> str:
    flags = []
    flags.extend(row.get("quality_flags") or [])
    if not row.get("kegiatan"):
        flags.append("MISSING_ACTIVITY")
    if not row.get("kode_akun") and not row.get("akun"):
        flags.append("MISSING_ACCOUNT")
    if pd.isna(row.get("jumlah")) or row.get("jumlah") is None:
        flags.append("MISSING_AMOUNT")
    return ";".join(flags) if flags else QUALITY_OK


def _append_quality_flag(existing: object, flag: str) -> str:
    parts = [part for part in str(existing or "").split(";") if part and part != QUALITY_OK]
    if flag not in parts:
        parts.append(flag)
    return ";".join(parts) if parts else QUALITY_OK


def _norm(value: object) -> str:
    return (normalize_text(value) or "").lower()


def classify_sheet_role(sheet_name: str) -> str:
    normalized = _norm(sheet_name)
    if normalized == "rab":
        return "main_rab"
    if normalized.startswith("contoh"):
        return "template_or_example"
    if "master" in normalized or "ket_akun" in normalized:
        return "mapping_or_reference"
    if any(token in normalized for token in ["iku", "rpd", "nomenklatur"]):
        return "mapping_or_reference"
    if any(
        token in normalized
        for token in [
            "belanja",
            "perjalanan dinas",
            "jasa profesi",
            "jasa lainnya",
            "honor",
            "sewa",
            "pemeliharaan",
            "persediaan",
        ]
    ):
        return "detail_support"
    if "rekap" in normalized:
        return "reconciliation"
    return "unknown"


def _formula_text(ws_formula: Worksheet | None, row_number: int, column_number: int) -> str | None:
    if ws_formula is None:
        return None
    value = ws_formula.cell(row=row_number, column=column_number).value
    return value if isinstance(value, str) and value.startswith("=") else None


def detect_formula_errors(formula: object) -> list[str]:
    text = str(formula or "")
    return [error for error in FORMULA_ERRORS if error in text]


def _collect_formula_errors(ws_formula: Worksheet, source: ExcelSource, tahun: str, periode: str | None) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    for row in ws_formula.iter_rows():
        for cell in row:
            formula = cell.value if isinstance(cell.value, str) and cell.value.startswith("=") else None
            for error in detect_formula_errors(formula):
                errors.append(
                    {
                        "tahun": tahun,
                        "periode": periode,
                        "source_file": source.path.name,
                        "source_sheet": ws_formula.title,
                        "source_row": cell.row,
                        "cell": f"{ws_formula.title}!{cell.coordinate}",
                        "validation_type": "FORMULA_ERROR",
                        "formula": formula,
                        "formula_error": error,
                        "severity": "high",
                        "reason": "formula_contains_error",
                    }
                )
    return errors


def _formula_references_in_column(formula: object, target_column: str = "P") -> set[int]:
    text = str(formula or "").replace("$", "")
    if not text:
        return set()
    rows: set[int] = set()
    target_idx = column_index_from_string(target_column)
    for match in re.finditer(r"([A-Z]{1,3}\d+:[A-Z]{1,3}\d+)", text, flags=re.I):
        try:
            min_col, min_row, max_col, max_row = range_boundaries(match.group(1).upper())
        except ValueError:
            continue
        if min_col <= target_idx <= max_col:
            rows.update(range(min_row, max_row + 1))
    for match in re.finditer(rf"\b{target_column}(\d+)\b", text, flags=re.I):
        rows.add(int(match.group(1)))
    return rows


def build_formula_coverage(ws_formula: Worksheet, target_column: str = "P") -> tuple[set[int], pd.DataFrame]:
    covered_rows: set[int] = set()
    records: list[dict[str, object]] = []
    target_idx = column_index_from_string(target_column)
    for row_number in range(1, ws_formula.max_row + 1):
        formula = _formula_text(ws_formula, row_number, target_idx)
        if not formula:
            continue
        rows = sorted(_formula_references_in_column(formula, target_column))
        covered_rows.update(rows)
        records.append(
            {
                "source_sheet": ws_formula.title,
                "source_row": row_number,
                "formula_cell": f"{target_column}{row_number}",
                "formula": formula,
                "covered_rows": rows,
                "formula_errors": detect_formula_errors(formula),
            }
        )
    return covered_rows, pd.DataFrame(records)


def classify_rab_row(ws_values: Worksheet, ws_formula: Worksheet | None, row_number: int) -> str:
    kode = normalize_text(ws_values.cell(row=row_number, column=1).value)
    uraian = normalize_text(ws_values.cell(row=row_number, column=2).value)
    jumlah = normalize_money(ws_values.cell(row=row_number, column=16).value)
    formula_p = _formula_text(ws_formula, row_number, 16)
    if not uraian and jumlah is None:
        return "blank_or_note"
    if _looks_like_total(uraian):
        return "total_row"
    if formula_p and kode:
        return "subtotal_row"
    if kode and jumlah is not None:
        return "subtotal_or_header"
    if not kode and uraian and jumlah is not None:
        return "leaf_item"
    return "blank_or_note"


def _row_visual_features(ws: Worksheet, row_number: int, max_column: int = 25) -> dict[str, object]:
    fills = []
    bold_count = 0
    thick_border = False
    merged_count = 0
    for column_number in range(1, min(ws.max_column, max_column) + 1):
        cell = ws.cell(row=row_number, column=column_number)
        color = getattr(cell.fill.fgColor, "rgb", None) or cell_fill_fallback(cell)
        if color:
            fills.append(str(color))
        bold_count += int(bool(cell.font.bold))
        thick_border = thick_border or any(
            getattr(getattr(cell.border, side), "style", None) in {"medium", "thick", "double"}
            for side in ("left", "right", "top", "bottom")
        )
        merged_count += int(any(rng.min_row <= row_number <= rng.max_row and rng.min_col <= column_number <= rng.max_col for rng in ws.merged_cells.ranges))
    colored = [fill for fill in fills if fill not in {"00000000", "FFFFFFFF"}]
    return {
        "row_fill_signature": "|".join(sorted(set(fills))) if fills else None,
        "row_font_bold_count": bold_count,
        "row_border_signature": "thick" if thick_border else "normal",
        "merged_context": str(merged_count) if merged_count else None,
        "is_visually_header": bool(colored and bold_count),
        "is_visually_detail": bool(not colored and bold_count <= 1),
    }


def cell_fill_fallback(cell: object) -> str | None:
    color = getattr(getattr(cell, "fill", None), "fgColor", None)
    if color is None:
        return None
    if getattr(color, "type", None) == "indexed":
        return f"indexed:{getattr(color, 'indexed', '')}"
    if getattr(color, "type", None) == "theme":
        return f"theme:{getattr(color, 'theme', '')}:{getattr(color, 'tint', '')}"
    return None


def _sheet_period(source: ExcelSource) -> str | None:
    if source.periode:
        return source.periode
    name = source.path.name.lower()
    if "jan" in name or "jun" in name:
        return "Jan-Jun"
    if "jul" in name or "des" in name or "dec" in name:
        return "Jul-Des"
    return None


def _extract_simple_rab_table(source: ExcelSource) -> pd.DataFrame:
    try:
        rab = pd.read_excel(source.path, sheet_name="RAB")
    except Exception:
        return pd.DataFrame()
    required = {"kode_akun", "nama_kegiatan", "total_pagu"}
    if not required.issubset(set(rab.columns)):
        return pd.DataFrame()
    tahun = str(detect_year_from_workbook(source.path, source.tahun_input) or source.tahun_input or "")
    rows = []
    month_cols = [col for col in rab.columns if str(col).lower() in {"jan", "feb", "mar", "apr", "mei", "jun", "jul", "agu", "sep", "okt", "nov", "des"}]
    for idx, record in rab.iterrows():
        jumlah = normalize_money(record.get("total_pagu"))
        rows.append(
            {
                "item_id": _stable_id([source.file_id, source.path.name, "RAB", idx, record.get("kode_akun"), record.get("nama_kegiatan")]),
                "tahun": tahun,
                "periode": _sheet_period(source),
                "prodi": source.prodi or "Sains Data",
                "source_file": source.path.name,
                "source_sheet": "RAB",
                "source_row": int(idx) + 2,
                "nomenklatur_path": normalize_text(record.get("kategori")),
                "kegiatan": normalize_text(record.get("nama_kegiatan")),
                "akun": f"{record.get('kode_akun')} - {record.get('kategori')}",
                "kode_akun": normalize_text(record.get("kode_akun")),
                "nama_akun": normalize_text(record.get("kategori")),
                "uraian_detail": normalize_text(record.get("nama_kegiatan")),
                "qty": 1,
                "satuan": "paket",
                "harga_satuan": jumlah,
                "jumlah": jumlah,
                "iku": None,
                "mapping_status": "source_table",
                "mapping_method": "simple_rab_sheet",
                "data_quality_flag": QUALITY_OK if jumlah is not None else "MISSING_AMOUNT",
                "raw_row_text": " | ".join(str(record.get(col)) for col in rab.columns if pd.notna(record.get(col))),
                "alokasi_bulanan": {str(col): normalize_money(record.get(col)) for col in month_cols},
            }
        )
    return pd.DataFrame(rows)


def _header_map(ws: Worksheet, row_number: int) -> dict[str, int]:
    mapping: dict[str, int] = {}
    amount_candidates: list[tuple[int, int]] = []
    for column_number in range(1, min(ws.max_column, 30) + 1):
        text = (normalize_text(ws.cell(row=row_number, column=column_number).value) or "").lower()
        if not text:
            continue
        if "urai" in text or "rincian" in text:
            mapping.setdefault("uraian", column_number)
        elif "supplier" in text or "penyedia" in text:
            mapping.setdefault("supplier", column_number)
        elif text in {"qty", "kuantitas", "volume"} or "qty" in text:
            mapping.setdefault("qty", column_number)
        elif "harga" in text:
            mapping.setdefault("harga_satuan", column_number)
        elif "satuan" in text:
            mapping.setdefault("satuan", column_number)
        score = _amount_header_score(text)
        if score:
            amount_candidates.append((column_number, score))
    amount_column = _select_amount_column(amount_candidates)
    if amount_column:
        mapping["jumlah"] = amount_column
        mapping["_jumlah_candidates"] = [column for column, _ in sorted(amount_candidates, key=lambda item: (-item[1], -item[0]))]
    return mapping


def _find_recent_header(ws: Worksheet, row_number: int) -> dict[str, int]:
    lower_bound = max(1, row_number - 30)
    for probe in range(row_number, lower_bound - 1, -1):
        header = _header_map(ws, probe)
        if "uraian" in header and ("jumlah" in header or "harga_satuan" in header):
            return header
    return {}


def _rightmost_amount_from_row(ws: Worksheet, row_number: int, header: dict[str, int]) -> float | None:
    candidate_columns = header.get("_jumlah_candidates") or []
    for column_number in candidate_columns:
        amount = normalize_money(ws.cell(row=row_number, column=column_number).value)
        if amount is not None:
            return amount

    lower_column = max(header.get("harga_satuan") or 1, header.get("qty") or 1)
    values = [
        normalize_money(ws.cell(row=row_number, column=column_number).value)
        for column_number in range(lower_column + 1, min(ws.max_column, 30) + 1)
    ]
    return next((value for value in reversed(values) if value is not None), None)


def _row_item_from_header(ws: Worksheet, row_number: int, header: dict[str, int]) -> dict[str, object] | None:
    if not header or "uraian" not in header:
        return None
    uraian = normalize_text(ws.cell(row=row_number, column=header["uraian"]).value)
    if not uraian or _looks_like_total(uraian):
        return None
    if uraian.lower() in {"uraian", "rincian"}:
        return None
    qty = normalize_money(ws.cell(row=row_number, column=header.get("qty", -1)).value) if header.get("qty") else None
    harga = normalize_money(ws.cell(row=row_number, column=header.get("harga_satuan", -1)).value) if header.get("harga_satuan") else None
    jumlah = normalize_money(ws.cell(row=row_number, column=header.get("jumlah", -1)).value) if header.get("jumlah") else None
    if jumlah is None:
        jumlah = _rightmost_amount_from_row(ws, row_number, header)
    if jumlah is None and qty is not None and harga is not None:
        jumlah = qty * harga
    if jumlah is None:
        return None
    return normalize_detail_amounts({
        "uraian_detail": uraian,
        "supplier": normalize_text(ws.cell(row=row_number, column=header.get("supplier", -1)).value) if header.get("supplier") else None,
        "qty": qty,
        "satuan": normalize_text(ws.cell(row=row_number, column=header.get("satuan", -1)).value) if header.get("satuan") else None,
        "harga_satuan": harga,
        "jumlah": jumlah,
    })


def _row_item_from_2025_layout(ws: Worksheet, row_number: int) -> dict[str, object] | None:
    uraian = normalize_text(ws.cell(row=row_number, column=2).value)
    qty = normalize_money(ws.cell(row=row_number, column=8).value)
    satuan = normalize_text(ws.cell(row=row_number, column=9).value)
    harga = normalize_money(ws.cell(row=row_number, column=11).value)
    jumlah = normalize_money(ws.cell(row=row_number, column=16).value) or normalize_money(ws.cell(row=row_number, column=14).value)
    if not uraian or _looks_like_total(uraian):
        return None
    if uraian.lower() in {"uraian", "rincian"}:
        return None
    if jumlah is None and qty is not None and harga is not None:
        jumlah = qty * harga
    if jumlah is None:
        return None
    return normalize_detail_amounts({"uraian_detail": uraian, "qty": qty, "satuan": satuan, "harga_satuan": harga, "jumlah": jumlah, "supplier": None})


def parse_rab_workbook(source: ExcelSource) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    simple = _extract_simple_rab_table(source)
    if not simple.empty:
        return simple, pd.DataFrame(), pd.DataFrame()

    wb = load_workbook(source.path, data_only=True, read_only=False)
    wb_formula = load_workbook(source.path, data_only=False, read_only=False)
    tahun = str(detect_year_from_workbook(source.path, source.tahun_input) or source.tahun_input or "")
    periode = _sheet_period(source)
    prodi = source.prodi or "Sains Data"
    items: list[dict[str, object]] = []
    hierarchy: list[dict[str, object]] = []
    validation: list[dict[str, object]] = []
    coverage_frames: list[pd.DataFrame] = []
    workbook_has_main_rab = any(classify_sheet_role(name) == "main_rab" for name in wb.sheetnames)

    for ws in wb.worksheets:
        ws_formula = wb_formula[ws.title] if ws.title in wb_formula.sheetnames else None
        sheet_lower = ws.title.lower()
        source_role = classify_sheet_role(ws.title)
        if ws_formula is not None:
            validation.extend(_collect_formula_errors(ws_formula, source, tahun, periode))
        if source_role in {"template_or_example", "mapping_or_reference"}:
            continue
        covered_rows: set[int] = set()
        if ws_formula is not None and source_role == "main_rab":
            covered_rows, coverage_df = build_formula_coverage(ws_formula, "P")
            if not coverage_df.empty:
                coverage_df["tahun"] = tahun
                coverage_df["periode"] = periode
                coverage_df["source_file"] = source.path.name
                coverage_frames.append(coverage_df)
        is_rekap_sheet = "rekap" in sheet_lower
        current = {
            "nomenklatur_path": None,
            "kegiatan": ws.title if not is_rekap_sheet and "prioritas" not in sheet_lower and "usulan" not in sheet_lower else None,
            "unit": prodi,
            "akun": None,
            "kode_akun": None,
            "nama_akun": None,
        }
        sheet_code, sheet_account = _split_account(ws.title)
        if sheet_code:
            current["kode_akun"] = sheet_code
            current["nama_akun"] = sheet_account
            current["akun"] = f"{sheet_code} - {sheet_account}" if sheet_account else sheet_code

        for row_number in range(1, ws.max_row + 1):
            text = row_text(ws, row_number, 35)
            if not text:
                continue
            color = dominant_row_color(ws, row_number, 25)
            short_color = color[2:] if color and color.startswith("FF") else color
            row_type = RAB_COLOR_LEVELS.get(color or "") or RAB_COLOR_LEVELS.get(short_color or "")
            row_account_code, row_account_name = _split_account(text)
            if row_type:
                hierarchy.append(
                    {
                        "tahun": tahun,
                        "periode": periode,
                        "prodi": prodi,
                        "source_file": source.path.name,
                        "source_sheet": ws.title,
                        "source_row": row_number,
                        "source_role": source_role,
                        "fill_color": color,
                        "row_type": row_type,
                        "row_text": text,
                    }
                )
            if row_type == "NOMENKLATUR":
                current["nomenklatur_path"] = text
                continue
            if row_type == "KEGIATAN":
                current["kegiatan"] = text
                continue
            if row_type == "UNIT":
                current["unit"] = text
                continue
            if row_type == "AKUN" or row_account_code:
                if row_account_code:
                    current["kode_akun"] = row_account_code
                    current["nama_akun"] = row_account_name
                    current["akun"] = f"{row_account_code} - {row_account_name}" if row_account_name else row_account_code
                elif row_type == "AKUN":
                    current["akun"] = text
                if row_type == "AKUN":
                    continue

            lowered = text.lower()
            if is_rekap_sheet:
                header = _find_recent_header(ws, row_number)
                amount = _rightmost_amount_from_row(ws, row_number, header) if header else None
                uraian_column = header.get("uraian") if header else None
                label = normalize_text(ws.cell(row=row_number, column=uraian_column).value) if uraian_column else text
                if amount is not None and label:
                    validation_type = "REKAP_FINAL_TOTAL" if _looks_like_total(label) else "REKAP_ACCOUNT_ROW"
                    if validation_type == "REKAP_FINAL_TOTAL" or "belanja" in label.lower() or row_account_code:
                        validation.append(
                            {
                                "tahun": tahun,
                                "periode": periode,
                                "source_file": source.path.name,
                                "source_sheet": ws.title,
                                "source_row": row_number,
                                "validation_type": validation_type,
                                "total_rekap": amount,
                                "row_text": text,
                            }
                        )
                continue

            if "kegiatan" in lowered and ":" in text and not _looks_like_total(text):
                current["kegiatan"] = text.split(":", 1)[1].strip() or current["kegiatan"]
                continue
            if _looks_like_total(text):
                amount_candidates = [normalize_money(ws.cell(row=row_number, column=col).value) for col in range(1, min(ws.max_column, 30) + 1)]
                total = next((value for value in reversed(amount_candidates) if value is not None), None)
                if total is not None:
                    validation.append(
                        {
                            "tahun": tahun,
                            "periode": periode,
                            "source_file": source.path.name,
                            "source_sheet": ws.title,
                            "source_row": row_number,
                            "validation_type": "SHEET_TOTAL_ROW",
                            "total_rekap": total,
                            "row_text": text,
                        }
                    )
                continue

            header = _find_recent_header(ws, row_number)
            parsed = _row_item_from_header(ws, row_number, header) or _row_item_from_2025_layout(ws, row_number)
            if not parsed:
                continue
            row_classification = classify_rab_row(ws, ws_formula, row_number) if source_role == "main_rab" else "leaf_item"
            if row_classification in {"subtotal_row", "subtotal_or_header", "total_row", "blank_or_note"}:
                validation.append(
                    {
                        "tahun": tahun,
                        "periode": periode,
                        "source_file": source.path.name,
                        "source_sheet": ws.title,
                        "source_row": row_number,
                        "source_role": source_role,
                        "validation_type": "RAB_ROW_CLASSIFICATION",
                        "row_type": row_classification,
                        "include_in_gold": False,
                        "total_rekap": parsed.get("jumlah"),
                        "row_text": text,
                    }
                )
                continue
            row_values = [ws.cell(row=row_number, column=column_number).value for column_number in range(1, min(ws.max_column, 35) + 1)]
            iku = _parse_iku_from_values(row_values)
            quality_flags: list[str] = []
            include_in_gold = source_role == "main_rab" or (not workbook_has_main_rab and source_role not in {"reconciliation", "template_or_example", "mapping_or_reference"})
            formula_p = _formula_text(ws_formula, row_number, 16)
            if source_role == "main_rab" and row_classification == "leaf_item" and row_number not in covered_rows:
                row_classification = "orphan_leaf_item"
                quality_flags.append("orphan_not_in_parent_sum")
                include_in_gold = False
            if source_role == "detail_support" and workbook_has_main_rab:
                quality_flags.append("detail_support_not_included_in_gold")
            if workbook_has_main_rab and source_role not in {"main_rab", "detail_support"}:
                include_in_gold = False
            quality_flags.extend(f"formula_{error.lower().replace('#', '').replace('!', '')}" for error in detect_formula_errors(formula_p))
            record = {
                "item_id": _stable_id([source.file_id, source.path.name, ws.title, row_number, parsed.get("uraian_detail")]),
                "tahun": tahun,
                "periode": periode,
                "prodi": prodi,
                "source_file": source.path.name,
                "source_sheet": ws.title,
                "source_row": row_number,
                "source_role": source_role,
                "row_type": row_classification,
                "include_in_gold": include_in_gold,
                "quality_flags": quality_flags,
                "formula_p": formula_p,
                **current,
                **parsed,
                "iku": iku,
                "mapping_status": "parsed" if current.get("kode_akun") else "manual_review",
                "mapping_method": "color_hierarchy" if row_type else "header_context",
                "raw_row_text": text,
                **_row_visual_features(ws, row_number),
            }
            record["data_quality_flag"] = _quality_flag(record)
            items.append(record)

    wb.close()
    wb_formula.close()
    item_df = pd.DataFrame(items)
    if not item_df.empty:
        item_df = normalize_detail_amount_frame(item_df)
        item_df["quality_flags"] = item_df["quality_flags"].map(lambda value: ";".join(value) if isinstance(value, list) else value)
        detail_total = item_df.groupby(["source_file"], dropna=False)["jumlah"].sum().reset_index(name="total_detail")
        validation_df = pd.DataFrame(validation)
        main_items = item_df[item_df["source_role"].eq("main_rab")] if "source_role" in item_df.columns else item_df.iloc[0:0]
        included_items = item_df[item_df["include_in_gold"].eq(True)] if "include_in_gold" in item_df.columns else item_df
        orphan_items = item_df[item_df["row_type"].eq("orphan_leaf_item")] if "row_type" in item_df.columns else item_df.iloc[0:0]
        detail_support = item_df[item_df["source_role"].eq("detail_support")] if "source_role" in item_df.columns else item_df.iloc[0:0]
        reconciliation_rows = [
            {
                "tahun": tahun,
                "periode": periode,
                "source_file": source.path.name,
                "source_sheet": "RAB",
                "validation_type": "RAB_RECONCILIATION_SUMMARY",
                "main_rab_leaf_total": float(main_items["jumlah"].sum()) if not main_items.empty else 0.0,
                "orphan_excluded_total": float(included_items["jumlah"].sum()) if not included_items.empty else 0.0,
                "detail_support_total": float(detail_support["jumlah"].sum()) if not detail_support.empty else 0.0,
                "orphan_rows": sorted(int(row) for row in orphan_items["source_row"].dropna().unique()) if not orphan_items.empty else [],
                "final_gold_total": float(included_items["jumlah"].sum()) if not included_items.empty else 0.0,
                "validation_status": "validated_with_warnings" if not orphan_items.empty or any(row.get("validation_type") == "FORMULA_ERROR" for row in validation) else "validated",
            }
        ]
        if coverage_frames:
            coverage_summary = pd.concat(coverage_frames, ignore_index=True, sort=False)
            validation_df = pd.concat([validation_df, coverage_summary.assign(validation_type="FORMULA_COVERAGE")], ignore_index=True, sort=False)
        validation_df = pd.concat([validation_df, pd.DataFrame(reconciliation_rows)], ignore_index=True, sort=False)
        rekap_candidates = validation_df[validation_df["validation_type"].eq("REKAP_FINAL_TOTAL")] if "validation_type" in validation_df.columns else pd.DataFrame()
        if rekap_candidates.empty and "validation_type" in validation_df.columns:
            rekap_candidates = validation_df[validation_df["validation_type"].eq("REKAP_ACCOUNT_ROW")]
        if not rekap_candidates.empty:
            rekap_total = rekap_candidates.groupby(["source_file"], dropna=False)["total_rekap"].sum().reset_index()
            detail_summary = detail_total.merge(rekap_total, on="source_file", how="outer").fillna(0)
            detail_summary["selisih"] = detail_summary["total_rekap"] - detail_summary["total_detail"]
            detail_summary["validation_status"] = detail_summary["selisih"].abs().apply(lambda value: "OK" if value < 1 else "REVIEW")
        else:
            detail_summary = detail_total
            detail_summary["total_rekap"] = None
            detail_summary["selisih"] = None
            detail_summary["validation_status"] = "NO_REKAP_TOTAL"
        detail_summary["validation_type"] = "DETAIL_TOTAL_SUMMARY"
        if not workbook_has_main_rab:
            validation_df = detail_summary
        elif validation_df.empty:
            validation_df = detail_summary
        else:
            validation_df = pd.concat([validation_df, detail_summary.dropna(axis=1, how="all")], ignore_index=True, sort=False)
    else:
        validation_df = pd.DataFrame(validation)
    return item_df, pd.DataFrame(hierarchy), validation_df
