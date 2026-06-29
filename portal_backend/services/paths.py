from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
PORTAL_DIR = ROOT_DIR / "portal"
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs"
ACTIVITY_LOG_PATH = OUTPUTS_DIR / "reports" / "activity_log.json"

PREVIEW_LAYER_DIRS = {
    "raw": DATA_DIR / "raw" / "excel_lakehouse",
    "bronze": DATA_DIR / "generated" / "bronze",
    "silver": DATA_DIR / "generated" / "silver",
    "gold": DATA_DIR / "generated" / "gold",
}

DEFAULT_PREVIEW_FILES = {
    "bronze": "bronze_excel_cells.csv",
    "silver": "silver_rab_items_flexible.csv",
    "gold": "fact_anggaran.csv",
}
