from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from openpyxl import load_workbook

from .files import read_json, write_json
from .paths import OUTPUTS_DIR, ROOT_DIR
from src.common.runtime_config import DEFAULT_SOURCE_EVENT_ISO, get_runtime_config


CONTEXT_PATH = OUTPUTS_DIR / "reports" / "active_runtime_context.json"
SCENARIO_MANIFEST_PATH = ROOT_DIR / "data" / "dummy_upload_skenario_multi_tahun" / "manifest_skenario.csv"

CONTEXT_ENV_MAP = {
    "target_prodi": "PORTAL_TARGET_PRODI",
    "target_fakultas": "PORTAL_TARGET_FAKULTAS",
    "target_tahun_akademik": "PORTAL_TARGET_TAHUN_AKADEMIK",
    "target_tahun_anggaran": "PORTAL_TARGET_TAHUN_ANGGARAN",
    "batch_id": "PORTAL_BATCH_ID",
    "source_event": "PORTAL_SOURCE_EVENT_ISO",
    "dummy_transaction_rows": "PORTAL_DUMMY_TRANSACTION_ROWS",
    "dummy_invalid_rows": "PORTAL_DUMMY_INVALID_ROWS",
    "target_total_piutang": "PORTAL_TARGET_TOTAL_PIUTANG",
    "target_jumlah_penunggak": "PORTAL_TARGET_JUMLAH_PENUNGGAK",
    "target_total_pagu_rab": "PORTAL_TARGET_TOTAL_PAGU_RAB",
}


def _target_label(context: Mapping[str, Any]) -> str:
    return f"{context.get('target_prodi', 'Sains Data')} - Tahun Akademik {context.get('target_tahun_akademik', '-')}"


def _batch_from_year(context: Mapping[str, Any]) -> str:
    year = str(context.get("target_tahun_anggaran") or "").strip()
    prodi = str(context.get("target_prodi") or "Sains Data").lower().replace(" ", "-")
    return f"batch-{prodi}-{year}" if year else "batch-upload-manual"


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).replace("_", "").strip()
    if not text:
        return None
    return int(float(text))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_number(value: Any) -> bool:
    try:
        text = str(value or "").strip()
        if not text:
            return False
        float(text)
        return True
    except ValueError:
        return False


def _is_iso_date(value: Any) -> bool:
    try:
        datetime.fromisoformat(str(value or "").strip())
        return True
    except ValueError:
        return False


def default_runtime_context() -> dict[str, Any]:
    config = get_runtime_config()
    context = {
        "target_prodi": config.target_prodi,
        "target_fakultas": config.target_fakultas,
        "target_tahun_akademik": config.target_tahun_akademik,
        "target_tahun_anggaran": config.target_tahun_anggaran,
        "batch_id": config.batch_id,
        "source_event": config.source_event_iso,
        "dummy_transaction_rows": config.dummy_transaction_rows,
        "dummy_invalid_rows": config.dummy_invalid_rows,
        "target_total_piutang": config.target_total_piutang,
        "target_jumlah_penunggak": config.target_jumlah_penunggak,
        "target_total_pagu_rab": config.target_total_pagu_rab,
        "source": "runtime_defaults",
    }
    context["target_label"] = config.target_label
    context["validation_mode"] = config.validation_mode
    return context


def normalize_context(payload: Mapping[str, Any] | None, base: Mapping[str, Any] | None = None, source: str = "manual") -> dict[str, Any]:
    base_context = dict(base or default_runtime_context())
    current = dict(base_context)
    payload = payload or {}
    supplied_batch_id = _string_or_none(payload.get("batch_id")) is not None
    old_year = base_context.get("target_tahun_anggaran")
    for key in [
        "target_prodi",
        "target_fakultas",
        "target_tahun_akademik",
        "target_tahun_anggaran",
        "batch_id",
        "source_event",
    ]:
        value = _string_or_none(payload.get(key))
        if value is not None:
            current[key] = value

    for key in [
        "dummy_transaction_rows",
        "dummy_invalid_rows",
        "target_total_piutang",
        "target_jumlah_penunggak",
        "target_total_pagu_rab",
    ]:
        value = _int_or_none(payload.get(key))
        if value is not None or key in {"target_total_piutang", "target_jumlah_penunggak"}:
            current[key] = value

    current["source_event"] = current.get("source_event") or DEFAULT_SOURCE_EVENT_ISO
    try:
        datetime.fromisoformat(str(current["source_event"]).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        current["source_event"] = DEFAULT_SOURCE_EVENT_ISO
    current["target_label"] = _target_label(current)
    year_changed_without_batch = not supplied_batch_id and old_year != current.get("target_tahun_anggaran")
    if year_changed_without_batch or not current.get("batch_id") or str(current.get("batch_id")).strip() in {"batch-dummy-20260526", "batch-upload-manual"}:
        current["batch_id"] = _batch_from_year(current)
    current["validation_mode"] = "observed_only" if current.get("target_total_piutang") is None and current.get("target_jumlah_penunggak") is None else "explicit_target"
    current["source"] = source
    return current


def read_active_context() -> dict[str, Any]:
    payload = read_json(CONTEXT_PATH)
    if isinstance(payload, dict) and not payload.get("_error"):
        return normalize_context(payload, base=default_runtime_context(), source=str(payload.get("source") or "saved"))
    return default_runtime_context()


def write_active_context(context: Mapping[str, Any], source: str = "manual") -> dict[str, Any]:
    normalized = normalize_context(context, base=read_active_context(), source=source)
    write_json(CONTEXT_PATH, normalized)
    return normalized


def context_from_form(form: Mapping[str, Any]) -> dict[str, Any] | None:
    payload = {key: form.get(key) for key in CONTEXT_ENV_MAP if form.get(key) not in (None, "")}
    return normalize_context(payload, base=read_active_context(), source="upload_form") if payload else None


def context_env(context: Mapping[str, Any] | None = None) -> dict[str, str]:
    context = context or read_active_context()
    env = {}
    for key, env_name in CONTEXT_ENV_MAP.items():
        value = context.get(key)
        if value is not None and str(value).strip():
            env[env_name] = str(value)
    return env


def period_metadata(context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or read_active_context()
    return {
        "target_prodi": context["target_prodi"],
        "target_fakultas": context["target_fakultas"],
        "target_tahun_akademik": context["target_tahun_akademik"],
        "target_tahun_anggaran": context["target_tahun_anggaran"],
        "target_label": context["target_label"],
        "batch_id": context["batch_id"],
        "source_event": context["source_event"],
    }


def scenario_manifest() -> list[dict[str, Any]]:
    if not SCENARIO_MANIFEST_PATH.exists():
        return []
    with SCENARIO_MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def infer_context_from_csv(paths: list[Path], base: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    years: set[str] = set()
    batches: set[str] = set()
    prodis: set[str] = set()
    fakultas: set[str] = set()
    total_rows = 0
    invalid_rows = 0
    for path in paths:
        if not path.exists() or path.suffix.lower() != ".csv":
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                total_rows += 1
                if row.get("tahun_akademik"):
                    years.add(row["tahun_akademik"].strip())
                if row.get("batch_id"):
                    batches.add(row["batch_id"].strip())
                if row.get("prodi"):
                    prodis.add(row["prodi"].strip())
                if row.get("fakultas"):
                    fakultas.add(row["fakultas"].strip())
                invalid_rows += int(
                    not (row.get("nim_dummy") or row.get("nim"))
                    or not _is_iso_date(row.get("tanggal"))
                    or not _is_number(row.get("nominal_bayar"))
                    or not _is_number(row.get("nominal_tagihan"))
                    or row.get("semester") not in {"Ganjil", "Genap"}
                    or row.get("jenis_biaya") not in {"UKT", "SPI"}
                    or row.get("status_bayar") not in {"paid", "partial", "unpaid", "failed"}
                )
    if not total_rows:
        return None
    payload: dict[str, Any] = {
        "dummy_transaction_rows": total_rows,
        "dummy_invalid_rows": invalid_rows,
    }
    if len(years) == 1:
        payload["target_tahun_akademik"] = next(iter(years))
    if len(batches) == 1:
        payload["batch_id"] = next(iter(batches))
    if len(prodis) == 1:
        payload["target_prodi"] = next(iter(prodis))
    if len(fakultas) == 1:
        payload["target_fakultas"] = next(iter(fakultas))
    return normalize_context(payload, base=base or read_active_context(), source="inferred_csv")


def infer_context_from_excel(path: Path, base: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    if not path.exists() or path.suffix.lower() != ".xlsx":
        return None
    payload: dict[str, Any] = {}
    workbook = load_workbook(path, read_only=True, data_only=True)
    if "metadata" in workbook.sheetnames:
        sheet = workbook["metadata"]
        rows = list(sheet.iter_rows(values_only=True))
        for key, value in rows[1:]:
            if key == "tahun_anggaran":
                payload["target_tahun_anggaran"] = value
            elif key == "prodi":
                payload["target_prodi"] = value
            elif key == "fakultas":
                payload["target_fakultas"] = value
    if "RAB" in workbook.sheetnames:
        sheet = workbook["RAB"]
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        if "total_pagu" in headers:
            idx = headers.index("total_pagu")
            total = sum((_int_or_none(row[idx].value) or 0) for row in sheet.iter_rows(min_row=2))
            payload["target_total_pagu_rab"] = total
    return normalize_context(payload, base=base or read_active_context(), source="inferred_excel") if payload else None
