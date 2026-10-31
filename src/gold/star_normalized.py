"""Modul star schema kanonik — menurunkan 4 dimensi + fact dari fact flat.

Atribut ``tahun`` disimpan langsung di fact (denormal), bukan dimensi waktu
terpisah, karena hanya 1 atribut waktu dan tidak ada hierarki temporal.
Input tidak pernah dimutasi (immutability).
"""

from __future__ import annotations

import pandas as pd

from src.gold.contract import FACT_COLUMNS as CONTRACT_FACT_COLUMNS
from src.gold.contract import STAR_DIM_SPEC, STAR_FACT_COLUMNS


def _norm(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _build_dimension(fact: pd.DataFrame, table: str) -> pd.DataFrame:
    spec = STAR_DIM_SPEC[table]
    key, natural = spec["key"], spec["natural"]
    if fact.empty:
        return pd.DataFrame(columns=[key, *natural])
    combos = (
        fact[natural]
        .copy()
        .drop_duplicates()
        .sort_values(by=natural, key=lambda series: series.map(_norm))
        .reset_index(drop=True)
    )
    keyed = combos.copy()
    keyed.insert(0, key, range(1, len(keyed) + 1))
    return keyed


def build_star_dimensions(fact: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Turunkan 5 tabel dimensi dari fact flat (tanpa memutasi input)."""

    source = fact.copy(deep=True)
    return {table: _build_dimension(source, table) for table in STAR_DIM_SPEC}


def build_star_fact(
    fact: pd.DataFrame, dims: dict[str, pd.DataFrame] | None = None
) -> pd.DataFrame:
    """Bangun fact ramping dengan FK surrogate deterministik."""

    if fact.empty:
        return pd.DataFrame(columns=STAR_FACT_COLUMNS)
    resolved = dims if dims is not None else build_star_dimensions(fact)
    keyed = fact.copy(deep=True)
    for table, spec in STAR_DIM_SPEC.items():
        key, natural = spec["key"], spec["natural"]
        lookup = {
            tuple(_norm(value) for value in row): int(keys)
            for row, keys in zip(
                resolved[table][natural].itertuples(index=False, name=None),
                resolved[table][key].tolist(),
            )
        }
        keyed[key] = [
            lookup[tuple(_norm(row[column]) for column in natural)]
            for row in keyed.to_dict(orient="records")
        ]
    keyed.insert(0, "fact_key", range(1, len(keyed) + 1))
    # Susun kolom persis sesuai kontrak STAR_FACT_COLUMNS.
    return pd.DataFrame(
        {
            column: keyed[column]
            if column in keyed.columns
            else pd.Series([None] * len(keyed))
            for column in STAR_FACT_COLUMNS
        }
    )


def build_gold_star(fact: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Bangun paket lengkap: 4 dim + 1 fact (tahun di fact, bukan dim_waktu)."""

    dims = build_star_dimensions(fact)
    return {**dims, "fact_anggaran": build_star_fact(fact, dims)}


def rebuild_flat_from_star(star: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Rekonstruksi frame flat CONTRACT_FACT_COLUMNS dari star (fact ⨝ 4 dim).

    Catatan: ``tahun`` sudah ada langsung di fact, tidak perlu join dim_waktu.
    Fungsi ini dipertahankan untuk referensi dan tes backward-compat.
    """
    split = star["fact_anggaran"]
    dims = {k: v for k, v in star.items() if k != "fact_anggaran"}

    result = split.copy(deep=True)
    for table, spec in STAR_DIM_SPEC.items():
        key = spec["key"]
        natural = spec["natural"]
        dim = dims[table]
        dim_subset = dim[[key] + natural].copy()
        result = result.merge(
            dim_subset,
            how="left",
            on=key,
            suffixes=("", f"__{table}"),
        )

    result = result.drop(columns=["fact_key", *[spec["key"] for spec in STAR_DIM_SPEC.values()]])

    for column in CONTRACT_FACT_COLUMNS:
        if column not in result.columns:
            result[column] = None

    result = result[[column for column in CONTRACT_FACT_COLUMNS if column in result.columns]]
    missing = [column for column in CONTRACT_FACT_COLUMNS if column not in result.columns]
    if missing:
        raise ValueError(f"Rebuild flat: kolom hilang {missing}")

    split_total = float(split["jumlah_weighted_iku"].sum())
    flat_total = float(result["jumlah_weighted_iku"].sum())
    if abs(split_total - flat_total) > 0.001:
        raise ValueError(
            f"Rebuild flat SUM(jumlah_weighted_iku) mismatch: fact={split_total} vs flat={flat_total}"
        )

    return result
