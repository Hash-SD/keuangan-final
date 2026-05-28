from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
PORTAL_DIR = ROOT_DIR / "portal"
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs"
ACTIVITY_LOG_PATH = OUTPUTS_DIR / "reports" / "activity_log.json"

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

