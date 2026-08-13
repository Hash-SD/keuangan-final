from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
import re


DEFAULT_SOURCE_EVENT_ISO = "2026-05-26T10:00:00+00:00"


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def _env_int(name: str, default: int | None = None) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value.replace("_", "").strip())


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value.strip())


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "target"


def _source_event() -> datetime:
    raw = _env("PORTAL_SOURCE_EVENT_ISO", DEFAULT_SOURCE_EVENT_ISO)
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass(frozen=True)
class RuntimeConfig:
    target_prodi: str
    target_fakultas: str
    target_tahun: str
    target_tahun_anggaran: str
    batch_id: str
    source_event: datetime
    target_total_pagu_rab: int

    @property
    def source_event_iso(self) -> str:
        return self.source_event.isoformat()

    @property
    def batch_year(self) -> str:
        return self.source_event.strftime("%Y")

    @property
    def target_label(self) -> str:
        return f"{self.target_prodi} - Tahun {self.target_tahun}"

    @property
    def validation_mode(self) -> str:
        return "excel_observed_only"

    @property
    def target_slug(self) -> str:
        return slugify(f"{self.target_prodi}_{self.target_tahun}")


def get_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        target_prodi=_env("PORTAL_TARGET_PRODI", "Sains Data"),
        target_fakultas=_env("PORTAL_TARGET_FAKULTAS", "Fakultas Sains"),
        target_tahun=_env("PORTAL_TARGET_TAHUN", "2024"),
        target_tahun_anggaran=_env("PORTAL_TARGET_TAHUN_ANGGARAN", "2024"),
        batch_id=_env("PORTAL_BATCH_ID", "batch-excel-lakehouse"),
        source_event=_source_event(),
        target_total_pagu_rab=_env_int("PORTAL_TARGET_TOTAL_PAGU_RAB", 150_000_000) or 150_000_000,
    )


def source_event_iso() -> str:
    return get_runtime_config().source_event_iso


def configured_batch_id() -> str:
    return get_runtime_config().batch_id


def configured_target_label() -> str:
    return get_runtime_config().target_label
