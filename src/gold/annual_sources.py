"""Annual source selection and overlap checks for the Gold build."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping


class AnnualSourceError(ValueError):
    """Raised when the annual source set cannot be selected safely."""

    def __init__(self, code: str, year: str, source_ids: Iterable[str]):
        self.code = code
        self.year = year
        self.source_ids = tuple(str(source_id) for source_id in source_ids)
        joined = ", ".join(self.source_ids)
        super().__init__(f"{code}: tahun {year} memiliki sumber bertabrakan [{joined}]")


@dataclass(frozen=True)
class AnnualSource:
    source_id: str
    year: str
    kind: str
    covers_source_ids: tuple[str, ...] = ()


def _kind(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return "annual" if normalized in {"", "tahunan", "annual", "yearly"} else "partial"


def select_annual_sources(records: Iterable[Mapping[str, object]]) -> tuple[AnnualSource, ...]:
    """Select one safe annual source set per year.

    A yearly workbook may replace partial sources only when its metadata proves
    that every partial source is covered.  Otherwise selection stops rather
    than silently preferring one file.
    """

    by_year: dict[str, list[AnnualSource]] = defaultdict(list)
    for record in records:
        source_id = str(record.get("source_id") or record.get("source_file") or "").strip()
        year = str(record.get("year") or record.get("tahun") or "").strip()
        if not source_id or not year:
            raise AnnualSourceError("MISSING_SOURCE_YEAR", year or "UNKNOWN", (source_id or "UNKNOWN",))
        covers = tuple(str(value) for value in (record.get("covers_source_ids") or ()))
        source = AnnualSource(source_id=source_id, year=year, kind=_kind(record.get("kind") or record.get("periode")), covers_source_ids=covers)
        by_year[year].append(source)

    selected: list[AnnualSource] = []
    for year, sources in sorted(by_year.items()):
        source_ids = [source.source_id for source in sources]
        if len(set(source_ids)) != len(source_ids):
            raise AnnualSourceError("DUPLICATE_SOURCE_IDENTITY", year, source_ids)
        annual = [source for source in sources if source.kind == "annual"]
        partial = [source for source in sources if source.kind == "partial"]
        if len(annual) > 1:
            raise AnnualSourceError("AMBIGUOUS_SOURCE_OVERLAP", year, [source.source_id for source in sources])
        if annual and partial:
            covered = set(annual[0].covers_source_ids)
            if not covered.issuperset(source.source_id for source in partial):
                raise AnnualSourceError("AMBIGUOUS_SOURCE_OVERLAP", year, [source.source_id for source in sources])
            selected.append(annual[0])
        else:
            selected.extend(sources)
    return tuple(selected)
