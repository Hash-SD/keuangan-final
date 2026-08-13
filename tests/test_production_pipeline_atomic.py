from __future__ import annotations

import pandas as pd

from src.gold.contract import FACT_COLUMNS
from src.validation.production_quality_gate import evaluate_gold_quality


def _row(**overrides):
    values = {column: None for column in FACT_COLUMNS}
    values.update(
        {
            "item_id": "a",
            "kode_iku": "IKU-1",
            "iku": "IKU-1",
            "jumlah": 100,
            "allocation_weight": 1,
            "jumlah_weighted_iku": 100,
            "dataset_session_id": "dataset-a",
            "run_id": "run-a",
            "tahun": "2025",
            "prodi": "SD",
            "kegiatan": "K",
            "uraian_detail": "U",
            "source_file": "x.xlsx",
            "source_sheet": "RAB",
            "source_row": 2,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    values.update(overrides)
    return values


def test_quality_gate_blocks_duplicate_gold_grain():
    fact = pd.DataFrame([_row(), _row()])

    result = evaluate_gold_quality(fact, "dataset-a", "run-a")

    assert result["status"] == "FAILED"
    assert "duplicate_fact_rows" in result["blocking_errors"]


def test_quality_gate_accepts_consistent_gold_row():
    fact = pd.DataFrame([_row()])

    assert evaluate_gold_quality(fact, "dataset-a", "run-a")["status"] == "PASSED"


def test_quality_gate_rejects_period_and_non_unit_allocation():
    row = _row(allocation_weight=0.5, jumlah_weighted_iku=50)
    row["periode"] = "Jan-Jun"
    result = evaluate_gold_quality(pd.DataFrame([row]), "dataset-a", "run-a")

    assert result["status"] == "FAILED"
    assert "gold_schema_mismatch" in result["blocking_errors"]
    assert "forbidden_gold_columns_present" in result["blocking_errors"]
    assert "allocation_weight_not_one_per_item" in result["blocking_errors"]
