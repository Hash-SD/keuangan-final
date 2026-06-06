from __future__ import annotations

import os
from pathlib import Path

from src.common.paths import DATA_DIR, GENERATED_DIR, RAW_DIR
from src.common.runtime_config import get_runtime_config


def _env_filename(name: str, default: str) -> str:
    value = os.getenv(name)
    filename = Path(value.strip()).name if value and value.strip() else default
    return filename or default


def raw_pdf_path() -> Path:
    return RAW_DIR / "pdf" / _env_filename("PORTAL_RAW_PDF_FILENAME", "ITERA_LKTA2024Audited.pdf")


def sample_pdf_path() -> Path:
    return DATA_DIR / "samples" / _env_filename("PORTAL_SAMPLE_PDF_FILENAME", raw_pdf_path().name)


def raw_rab_path() -> Path:
    return RAW_DIR / "excel" / _env_filename("PORTAL_RAB_FILENAME", "rab_prodi_sains_data.xlsx")


def silver_rab_path() -> Path:
    return GENERATED_DIR / "silver" / _env_filename("PORTAL_SILVER_RAB_FILENAME", "rab_prodi_sains_data_long.csv")


def active_period_metadata() -> dict[str, str]:
    config = get_runtime_config()
    return {
        "target_prodi": config.target_prodi,
        "target_fakultas": config.target_fakultas,
        "target_tahun_akademik": config.target_tahun_akademik,
        "target_tahun_anggaran": config.target_tahun_anggaran,
        "target_label": config.target_label,
        "batch_id": config.batch_id,
        "source_event": config.source_event_iso,
    }
