from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

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
    if not row.get("kegiatan"):
        flags.append("MISSING_ACTIVITY")
    if not row.get("kode_akun") and not row.get("akun"):
        flags.append("MISSING_ACCOUNT")
    if pd.isna(row.get("jumlah")) or row.get("jumlah") is None:
        flags.append("MISSING_AMOUNT")
    return ";".join(flags) if flags else QUALITY_OK


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
                "item_id": _stable_id([source.path.name, "RAB", idx, record.get("kode_akun"), record.get("nama_kegiatan")]),
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
    return {
        "uraian_detail": uraian,
        "supplier": normalize_text(ws.cell(row=row_number, column=header.get("supplier", -1)).value) if header.get("supplier") else None,
        "qty": qty,
        "satuan": normalize_text(ws.cell(row=row_number, column=header.get("satuan", -1)).value) if header.get("satuan") else None,
        "harga_satuan": harga,
        "jumlah": jumlah,
    }


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
    return {"uraian_detail": uraian, "qty": qty, "satuan": satuan, "harga_satuan": harga, "jumlah": jumlah, "supplier": None}


def parse_rab_workbook(source: ExcelSource) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    simple = _extract_simple_rab_table(source)
    if not simple.empty:
        return simple, pd.DataFrame(), pd.DataFrame()

    wb = load_workbook(source.path, data_only=True, read_only=False)
    tahun = str(detect_year_from_workbook(source.path, source.tahun_input) or source.tahun_input or "")
    periode = _sheet_period(source)
    prodi = source.prodi or "Sains Data"
    items: list[dict[str, object]] = []
    hierarchy: list[dict[str, object]] = []
    validation: list[dict[str, object]] = []

    for ws in wb.worksheets:
        sheet_lower = ws.title.lower()
        if sheet_lower.startswith("contoh"):
            continue
        if "master" in sheet_lower or "ket_akun" in sheet_lower:
            continue
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
            row_values = [ws.cell(row=row_number, column=column_number).value for column_number in range(1, min(ws.max_column, 35) + 1)]
            iku = _parse_iku_from_values(row_values)
            record = {
                "item_id": _stable_id([source.path.name, ws.title, row_number, parsed.get("uraian_detail")]),
                "tahun": tahun,
                "periode": periode,
                "prodi": prodi,
                "source_file": source.path.name,
                "source_sheet": ws.title,
                "source_row": row_number,
                **current,
                **parsed,
                "iku": iku,
                "mapping_status": "parsed" if current.get("kode_akun") else "manual_review",
                "mapping_method": "color_hierarchy" if row_type else "header_context",
                "raw_row_text": text,
            }
            record["data_quality_flag"] = _quality_flag(record)
            items.append(record)

    wb.close()
    item_df = pd.DataFrame(items)
    if not item_df.empty:
        detail_total = item_df.groupby(["source_file"], dropna=False)["jumlah"].sum().reset_index(name="total_detail")
        validation_df = pd.DataFrame(validation)
        if not validation_df.empty:
            rekap_candidates = validation_df[validation_df["validation_type"].eq("REKAP_FINAL_TOTAL")]
            if rekap_candidates.empty:
                rekap_candidates = validation_df[validation_df["validation_type"].eq("REKAP_ACCOUNT_ROW")]
            if not rekap_candidates.empty:
                rekap_total = rekap_candidates.groupby(["source_file"], dropna=False)["total_rekap"].sum().reset_index()
                validation_df = detail_total.merge(rekap_total, on="source_file", how="outer").fillna(0)
                validation_df["selisih"] = validation_df["total_rekap"] - validation_df["total_detail"]
                validation_df["validation_status"] = validation_df["selisih"].abs().apply(lambda value: "OK" if value < 1 else "REVIEW")
            else:
                validation_df = detail_total
                validation_df["total_rekap"] = None
                validation_df["selisih"] = None
                validation_df["validation_status"] = "NO_REKAP_TOTAL"
        else:
            validation_df = detail_total
            validation_df["total_rekap"] = None
            validation_df["selisih"] = None
            validation_df["validation_status"] = "NO_REKAP_TOTAL"
    else:
        validation_df = pd.DataFrame(validation)
    return item_df, pd.DataFrame(hierarchy), validation_df
