from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .files import read_json, relative_path, write_json
from .paths import OUTPUTS_DIR, ROOT_DIR
from src.common.time_utils import utc_now_iso


GOLD_PATH = ROOT_DIR / "data" / "generated" / "gold" / "fact_anggaran.parquet"
SILVER_PATH = ROOT_DIR / "data" / "generated" / "silver" / "silver_rab_items_flexible.parquet"
NOMENKLATUR_PATH = ROOT_DIR / "data" / "generated" / "silver" / "silver_nomenklatur_detail.parquet"
OVERRIDE_PATH = OUTPUTS_DIR / "reports" / "iku_review_overrides.json"


def _read_table(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            pass
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        try:
            return pd.read_csv(csv_path)
        except Exception:
            pass
    return pd.DataFrame()


def iku_review_queue(limit: int = 100) -> dict[str, Any]:
    silver = _read_table(SILVER_PATH)
    fact = _read_table(GOLD_PATH)
    nomen = _read_table(NOMENKLATUR_PATH)
    overrides = read_json(OVERRIDE_PATH) or {"overrides": {}}

    if silver.empty:
        return {"status": "empty", "rows": [], "iku_options": [], "summary": {"total_review": 0}}

    review_mask = (
        silver.get("mapping_status", pd.Series(dtype=str)).astype(str).str.contains("suggested_review|needs_review|review_queue", case=False, na=False)
        | silver.get("data_quality_flag", pd.Series(dtype=str)).astype(str).str.contains("REVIEW_QUEUE|MISSING_ACCOUNT|IKU_REVIEW_REQUIRED|IKU_SUGGESTED_REVIEW", case=False, regex=True, na=False)
    )
    review = silver[review_mask].copy()
    review = review.sort_values(["tahun", "source_file", "source_sheet", "source_row"], kind="stable")

    cols = [
        "item_id",
        "tahun",
        "source_file",
        "source_sheet",
        "source_row",
        "kegiatan",
        "uraian_detail",
        "akun",
        "jumlah",
        "kode_iku",
        "nama_iku",
        "nomenklatur_detail_id",
        "mapping_status",
        "mapping_method",
        "data_quality_flag",
    ]
    row_frame = review[[col for col in cols if col in review.columns]].head(limit)
    rows = row_frame.where(pd.notna(row_frame), None).to_dict(orient="records")

    options = []
    if not nomen.empty:
        option_cols = ["detail_id", "detail_kegiatan", "iku_raw", "nomenklatur_path"]
        available = nomen[[col for col in option_cols if col in nomen.columns]].dropna(subset=["iku_raw"], how="any").drop_duplicates()
        options = available.head(300).where(pd.notna(available), None).to_dict(orient="records")

    literal_review = 0
    if not fact.empty:
        literal_review = int(fact.astype(str).apply(lambda s: s.str.contains("IKU_REVIEW_REQUIRED|Perlu review IKU", case=False, regex=True, na=False)).any(axis=1).sum())

    return {
        "status": "ready",
        "source": {
            "silver": relative_path(SILVER_PATH),
            "gold": relative_path(GOLD_PATH),
            "overrides": relative_path(OVERRIDE_PATH),
        },
        "summary": {
            "total_review": int(len(review)),
            "returned": len(rows),
            "literal_iku_review_rows_in_gold": literal_review,
            "overrides": len((overrides.get("overrides") or {}) if isinstance(overrides, dict) else {}),
        },
        "rows": rows,
        "iku_options": options,
    }


def mapping_review_queue(limit: int = 100) -> dict[str, Any]:
    payload = iku_review_queue(limit=limit)
    payload["review_type"] = "akun_iku"
    payload["account_options"] = [
        {"kode_akun": "521111", "nama_akun": "Belanja Keperluan Perkantoran"},
        {"kode_akun": "521211", "nama_akun": "Belanja Bahan"},
        {"kode_akun": "521219", "nama_akun": "Belanja Barang Non Operasional"},
        {"kode_akun": "521811", "nama_akun": "Belanja Barang Persediaan"},
        {"kode_akun": "522141", "nama_akun": "Belanja Sewa"},
        {"kode_akun": "522151", "nama_akun": "Belanja Jasa Profesi"},
        {"kode_akun": "522191", "nama_akun": "Belanja Jasa Lainnya"},
        {"kode_akun": "524111", "nama_akun": "Belanja Perjalanan Dinas"},
    ]
    return payload


def save_iku_override(payload: dict[str, Any]) -> dict[str, Any]:
    item_id = str(payload.get("item_id") or "").strip()
    iku_codes = str(payload.get("iku_codes") or payload.get("iku_raw") or "").strip()
    if not item_id:
        raise ValueError("item_id wajib diisi.")
    if not iku_codes:
        raise ValueError("IKU wajib dipilih.")

    current = read_json(OVERRIDE_PATH) or {"overrides": {}}
    overrides = current.get("overrides") if isinstance(current, dict) else {}
    if not isinstance(overrides, dict):
        overrides = {}
    overrides[item_id] = {
        "item_id": item_id,
        "iku_codes": iku_codes,
        "detail_id": payload.get("detail_id"),
        "detail_kegiatan": payload.get("detail_kegiatan"),
        "nomenklatur_path": payload.get("nomenklatur_path"),
        "review_note": payload.get("review_note"),
        "reviewed_by": payload.get("reviewed_by") or "local_user",
        "updated_at": utc_now_iso(),
    }
    result = {"updated_at": utc_now_iso(), "overrides": overrides}
    write_json(OVERRIDE_PATH, result)
    return {"status": "saved", "override": overrides[item_id], "path": relative_path(OVERRIDE_PATH)}
