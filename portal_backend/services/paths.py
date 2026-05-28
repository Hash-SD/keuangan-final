from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
PORTAL_DIR = ROOT_DIR / "portal"
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs"
ACTIVITY_LOG_PATH = OUTPUTS_DIR / "reports" / "activity_log.json"
PDF_SAMPLE_PATH = DATA_DIR / "samples" / "ITERA_LKTA2024Audited.pdf"
RAW_PDF_PATH = DATA_DIR / "raw" / "pdf" / "ITERA_LKTA2024Audited.pdf"
RAW_EXCEL_RAB_PATH = DATA_DIR / "raw" / "excel" / "rab_prodi_sains_data.xlsx"
RAW_CSV_DIR = DATA_DIR / "raw" / "csv"
MASTER_UKT_PATH = DATA_DIR / "generated" / "master_ukt_itera.csv"
MASTER_SPI_PATH = DATA_DIR / "generated" / "master_spi_itera.csv"
DUMMY_MAHASISWA_PATH = DATA_DIR / "generated" / "dummy_mahasiswa_itera.csv"
MASTER_BIAYA_EXCEL_PATH = DATA_DIR / "raw" / "excel" / "master_biaya_itera.xlsx"

UPLOAD_DIRS = {
    "pdf": DATA_DIR / "raw" / "pdf",
    "csv": DATA_DIR / "raw" / "csv",
    "excel": DATA_DIR / "raw" / "excel",
}

PREVIEW_LAYER_DIRS = {
    "raw": DATA_DIR / "raw" / "csv",
    "bronze": DATA_DIR / "generated" / "bronze",
    "silver": DATA_DIR / "generated" / "silver",
    "gold": DATA_DIR / "generated" / "gold",
}

DEFAULT_PREVIEW_FILES = {
    "silver": "fact_piutang_ukt_prodi.csv",
    "gold": "vw_dashboard_piutang_ukt.csv",
}
