from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from src.excel_ingestion.excel_cell_extractor import ExcelSource, cell_fill_color, normalize_text


LEVEL_BY_COLOR = {
    "FFB4A7D6": "KEGIATAN",
    "FFF6B26B": "KRO",
    "FF93C47D": "RO",
    "FF76A5AF": "KOMPONEN",
    "FFC27BA0": "SUB_KOMPONEN",
}


def _key_part(value: object) -> str:
    text = normalize_text(value) or "NA"
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "NA"


def _build_detail_id(parts: list[object]) -> str:
    key = "|".join(_key_part(part) for part in parts)
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _split_iku(iku_raw: object) -> list[str]:
    text = normalize_text(iku_raw)
    if not text:
        return []
    return [item for item in (normalize_text(part) for part in re.split(r";|,|\n", text)) if item]


def parse_nomenklatur_workbook(source: ExcelSource) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wb = load_workbook(source.path, data_only=True, read_only=False)
    ws = wb["Nomenklatur FS"] if "Nomenklatur FS" in wb.sheetnames else wb[wb.sheetnames[0]]
    current = {
        "kegiatan_kode": None,
        "kegiatan_nomenklatur": None,
        "kro_kode": None,
        "kro_nomenklatur": None,
        "ro_kode": None,
        "ro_nomenklatur": None,
        "sumber_dana": None,
        "komponen_kode": None,
        "komponen_nomenklatur": None,
        "sub_komponen_kode": None,
        "sub_komponen_nomenklatur": None,
        "iku_raw": None,
    }
    details: list[dict[str, object]] = []
    structure: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    tahun = str(source.tahun_input or "")
    prodi = source.prodi or "Sains Data"

    for row_number in range(1, ws.max_row + 1):
        b = ws[f"B{row_number}"]
        c = ws[f"C{row_number}"]
        d = ws[f"D{row_number}"]
        e = ws[f"E{row_number}"]
        f = ws[f"F{row_number}"]
        detected_fill = cell_fill_color(b) or cell_fill_color(c) or cell_fill_color(d)
        level = LEVEL_BY_COLOR.get(detected_fill or "")
        kode = normalize_text(c.value)
        nama = normalize_text(d.value)
        iku = normalize_text(e.value)
        sumber_dana = normalize_text(f.value)

        if level:
            structure.append(
                {
                    "tahun": tahun,
                    "prodi": prodi,
                    "source_file": source.path.name,
                    "source_sheet": ws.title,
                    "source_row": row_number,
                    "detected_fill": detected_fill,
                    "detected_level": level,
                    "kode": kode,
                    "nomenklatur": nama,
                    "iku_raw": iku,
                    "sumber_dana": sumber_dana,
                }
            )
        elif detected_fill and nama:
            warnings.append(
                {
                    "source_file": source.path.name,
                    "source_sheet": ws.title,
                    "source_row": row_number,
                    "warning_type": "UNKNOWN_COLOR",
                    "warning_message": "Baris memiliki isi tetapi warna tidak ada di konfigurasi nomenklatur.",
                    "raw_value": nama,
                    "detected_color": detected_fill,
                }
            )

        if level == "KEGIATAN":
            current.update(
                {
                    "kegiatan_kode": kode,
                    "kegiatan_nomenklatur": nama,
                    "kro_kode": None,
                    "kro_nomenklatur": None,
                    "ro_kode": None,
                    "ro_nomenklatur": None,
                    "sumber_dana": None,
                    "komponen_kode": None,
                    "komponen_nomenklatur": None,
                    "sub_komponen_kode": None,
                    "sub_komponen_nomenklatur": None,
                    "iku_raw": None,
                }
            )
        elif level == "KRO":
            current.update(
                {
                    "kro_kode": kode,
                    "kro_nomenklatur": nama,
                    "ro_kode": None,
                    "ro_nomenklatur": None,
                    "sumber_dana": None,
                    "komponen_kode": None,
                    "komponen_nomenklatur": None,
                    "sub_komponen_kode": None,
                    "sub_komponen_nomenklatur": None,
                    "iku_raw": None,
                }
            )
        elif level == "RO":
            current.update(
                {
                    "ro_kode": kode,
                    "ro_nomenklatur": nama,
                    "sumber_dana": sumber_dana or current.get("sumber_dana"),
                    "komponen_kode": None,
                    "komponen_nomenklatur": None,
                    "sub_komponen_kode": None,
                    "sub_komponen_nomenklatur": None,
                    "iku_raw": None,
                }
            )
        elif level == "KOMPONEN":
            current.update(
                {
                    "komponen_kode": kode,
                    "komponen_nomenklatur": nama,
                    "sub_komponen_kode": None,
                    "sub_komponen_nomenklatur": None,
                    "iku_raw": None,
                }
            )
        elif level == "SUB_KOMPONEN":
            current.update({"sub_komponen_kode": kode, "sub_komponen_nomenklatur": nama, "iku_raw": iku or current.get("iku_raw")})
        elif nama:
            detail_id = _build_detail_id([tahun, prodi, *current.values(), nama])
            path_parts = [
                current.get("kegiatan_nomenklatur"),
                current.get("kro_nomenklatur"),
                current.get("ro_nomenklatur"),
                current.get("komponen_nomenklatur"),
                current.get("sub_komponen_nomenklatur"),
                nama,
            ]
            path = " > ".join(str(part) for part in path_parts if part)
            details.append(
                {
                    "tahun": tahun,
                    "prodi": prodi,
                    "detail_id": detail_id,
                    "source_file": source.path.name,
                    "source_sheet": ws.title,
                    "source_row": row_number,
                    **current,
                    "detail_kegiatan": nama,
                    "nomenklatur_path": path,
                    "nomenklatur_key": "|".join(_key_part(part) for part in [tahun, prodi, *current.values(), nama]),
                }
            )

    bridge_rows: list[dict[str, object]] = []
    for row in details:
        iku_codes = _split_iku(row.get("iku_raw"))
        if not iku_codes:
            continue
        weight = 1 / len(iku_codes)
        for idx, iku_kode in enumerate(iku_codes, start=1):
            bridge_rows.append(
                {
                    "tahun": row["tahun"],
                    "prodi": row["prodi"],
                    "detail_id": row["detail_id"],
                    "iku_kode": iku_kode,
                    "iku_urutan": idx,
                    "iku_count": len(iku_codes),
                    "allocation_weight": weight,
                    "allocation_method": "equal_split",
                    "source_file": row["source_file"],
                }
            )
    wb.close()
    return pd.DataFrame(details), pd.DataFrame(bridge_rows), pd.DataFrame(warnings or structure)
