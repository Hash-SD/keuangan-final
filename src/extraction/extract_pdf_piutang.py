from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR, RAW_DIR, ensure_parent
from src.common.runtime_config import configured_batch_id
from src.common.runtime_paths import raw_pdf_path


PDF_INPUT = raw_pdf_path()
SILVER_DIM_KUALITAS = GENERATED_DIR / "silver" / "dim_kualitas_piutang.csv"
SILVER_FACT_PIUTANG = GENERATED_DIR / "silver" / "fact_piutang_ukt_prodi.csv"
CONTROL_TOTAL_JSON = OUTPUTS_DIR / "metrics" / "master_control_total.json"
EXTRACTION_LOG = OUTPUTS_DIR / "metrics" / "pdf_extraction_log.json"


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _read_pages(pdf_path: str | Path) -> list[dict[str, object]]:
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            pages.append({"page_number": idx, "text": page.extract_text() or ""})
    return pages


def _parse_idr(value: str) -> int:
    return int(re.sub(r"[^\d]", "", value))


def extract_master_control_total(pdf_path: str | Path = PDF_INPUT) -> dict:
    controls = {
        "pendapatan_pnbp": None,
        "total_piutang_mahasiswa": None,
        "jumlah_mahasiswa_penunggak": None,
        "source_pages": [],
        "errors": [],
    }
    pages = _read_pages(pdf_path)
    patterns = {
        "pendapatan_pnbp": r"Pendapatan Penerimaan Negara Bukan Pajak:\s*Rp([\d.]+)",
        "total_piutang_mahasiswa": r"Total piutang mahasiswa pada tabel reviu piutang:\s*Rp([\d.]+)",
        "jumlah_mahasiswa_penunggak": r"Total mahasiswa penunggak:\s*(\d+)",
    }
    for page in pages:
        text = str(page["text"])
        if any(keyword in text for keyword in ["Laporan Realisasi Anggaran", "Catatan Hasil Reviu", "Piutang"]):
            controls["source_pages"].append(page["page_number"])
            for key, pattern in patterns.items():
                if controls[key] is None:
                    match = re.search(pattern, text)
                    if match:
                        controls[key] = _parse_idr(match.group(1))
    for key in patterns:
        if controls[key] is None:
            controls["errors"].append(f"Pattern not found: {key}")
    write_json(CONTROL_TOTAL_JSON, controls)
    write_json(EXTRACTION_LOG, {"errors": controls["errors"], "source_pages": controls["source_pages"]})
    return controls


def extract_dim_kualitas_piutang(pdf_path: str | Path = PDF_INPUT) -> pd.DataFrame:
    rows = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if "Tabel 1 Kriteria Piutang" not in text:
                continue
            table = page.extract_table() or []
            for raw in table[1:]:
                cells = [clean_text(cell) for cell in raw]
                if len(cells) >= 3 and cells[0] in {"Lancar", "Kurang Lancar", "Diragukan", "Macet"}:
                    rows.append(
                        {
                            "kualitas": cells[0],
                            "kriteria": cells[1],
                            "persentase_penyisihan": float(cells[2].replace("%", "")),
                            "source_page": page_idx,
                        }
                    )
            break
    if not rows:
        rows = [
            {"kualitas": "Lancar", "kriteria": "Tunggakan sampai 1 semester", "persentase_penyisihan": 0.5, "source_page": None},
            {"kualitas": "Kurang Lancar", "kriteria": "Tunggakan 2 sampai 3 semester", "persentase_penyisihan": 10.0, "source_page": None},
            {"kualitas": "Diragukan", "kriteria": "Tunggakan 4 sampai 5 semester", "persentase_penyisihan": 50.0, "source_page": None},
            {"kualitas": "Macet", "kriteria": "Tunggakan lebih dari 5 semester", "persentase_penyisihan": 100.0, "source_page": None},
        ]
    df = pd.DataFrame(rows).drop_duplicates("kualitas").reset_index(drop=True)
    df.insert(0, "kualitas_piutang_key", range(1, len(df) + 1))
    ensure_parent(SILVER_DIM_KUALITAS)
    df.to_csv(SILVER_DIM_KUALITAS, index=False)
    return df


def extract_fact_piutang_ukt_prodi(pdf_path: str | Path = PDF_INPUT) -> pd.DataFrame:
    master = GENERATED_DIR / "dummy_piutang_master.csv"
    if master.exists():
        df = pd.read_csv(master, dtype={"nim": "string"})
    else:
        rows = []
        pattern = re.compile(
            r"(SD|DM)\d{8}\s+(.+?)\s+(Fakultas .+?)\s+([A-Za-z ]+?)\s+(Ganjil|Genap)\s+(\d{4}/\d{4})\s+(\d+)\s+(Lancar|Kurang Lancar|Diragukan|Macet)\s+([\d.]+)\s+([\d.]+)"
        )
        for page in _read_pages(pdf_path):
            for match in pattern.finditer(str(page["text"])):
                rows.append(match.groups())
        df = pd.DataFrame(rows)
    df["source_filename"] = Path(pdf_path).name
    df["batch_id"] = configured_batch_id()
    ensure_parent(SILVER_FACT_PIUTANG)
    df.to_csv(SILVER_FACT_PIUTANG, index=False)
    return df


def main() -> None:
    extract_master_control_total()
    extract_dim_kualitas_piutang()
    extract_fact_piutang_ukt_prodi()


if __name__ == "__main__":
    main()
