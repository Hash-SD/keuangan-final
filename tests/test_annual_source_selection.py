from __future__ import annotations

import pytest

from src.gold.annual_sources import AnnualSourceError, select_annual_sources


def test_one_annual_workbook_is_selected_for_a_year():
    selected = select_annual_sources([{"source_id": "rab-2025.xlsx", "year": 2025, "kind": "Tahunan"}])

    assert [source.source_id for source in selected] == ["rab-2025.xlsx"]


def test_two_partial_workbooks_are_merged_when_their_source_ids_are_distinct():
    selected = select_annual_sources(
        [
            {"source_id": "rab-2023-jan-jun.xlsx", "year": 2023, "kind": "Jan-Jun"},
            {"source_id": "rab-2023-jul-des.xlsx", "year": 2023, "kind": "Jul-Des"},
        ]
    )

    assert {source.source_id for source in selected} == {"rab-2023-jan-jun.xlsx", "rab-2023-jul-des.xlsx"}


def test_annual_workbook_replaces_partials_only_with_explicit_coverage():
    selected = select_annual_sources(
        [
            {
                "source_id": "rab-2023-annual.xlsx",
                "year": 2023,
                "kind": "Tahunan",
                "covers_source_ids": ("rab-2023-jan-jun.xlsx", "rab-2023-jul-des.xlsx"),
            },
            {"source_id": "rab-2023-jan-jun.xlsx", "year": 2023, "kind": "Jan-Jun"},
            {"source_id": "rab-2023-jul-des.xlsx", "year": 2023, "kind": "Jul-Des"},
        ]
    )

    assert [source.source_id for source in selected] == ["rab-2023-annual.xlsx"]


def test_annual_and_partial_overlap_without_coverage_is_ambiguous():
    with pytest.raises(AnnualSourceError, match="AMBIGUOUS_SOURCE_OVERLAP") as error:
        select_annual_sources(
            [
                {"source_id": "rab-2023-annual.xlsx", "year": 2023, "kind": "Tahunan"},
                {"source_id": "rab-2023-jan-jun.xlsx", "year": 2023, "kind": "Jan-Jun"},
            ]
        )

    assert error.value.code == "AMBIGUOUS_SOURCE_OVERLAP"
    assert error.value.source_ids == ("rab-2023-annual.xlsx", "rab-2023-jan-jun.xlsx")


def test_all_sources_need_a_year_and_years_are_processed_independently():
    selected = select_annual_sources(
        [
            {"source_id": "rab-2024.xlsx", "year": 2024, "kind": "Tahunan"},
            {"source_id": "rab-2025.xlsx", "year": 2025, "kind": "Tahunan"},
        ]
    )

    assert [(source.year, source.source_id) for source in selected] == [("2024", "rab-2024.xlsx"), ("2025", "rab-2025.xlsx")]
    with pytest.raises(AnnualSourceError, match="MISSING_SOURCE_YEAR"):
        select_annual_sources([{"source_id": "unknown.xlsx", "kind": "Tahunan"}])
