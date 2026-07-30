from __future__ import annotations

import pandas as pd

from src.validation.production_quality_gate import evaluate_gold_quality


def test_quality_gate_blocks_duplicate_gold_grain():
    fact = pd.DataFrame(
        [
            {"item_id": "a", "kode_iku": "IKU-1", "jumlah": 100, "allocation_weight": 1, "jumlah_weighted_iku": 100, "dataset_session_id": "dataset-a", "run_id": "run-a", "tahun": "2025", "prodi": "SD", "kegiatan": "K", "uraian_detail": "U", "source_file": "x.xlsx", "source_sheet": "RAB", "source_row": 2, "created_at": "2026-01-01T00:00:00+00:00"},
            {"item_id": "a", "kode_iku": "IKU-1", "jumlah": 100, "allocation_weight": 1, "jumlah_weighted_iku": 100, "dataset_session_id": "dataset-a", "run_id": "run-a", "tahun": "2025", "prodi": "SD", "kegiatan": "K", "uraian_detail": "U", "source_file": "x.xlsx", "source_sheet": "RAB", "source_row": 2, "created_at": "2026-01-01T00:00:00+00:00"},
        ]
    )

    result = evaluate_gold_quality(fact, "dataset-a", "run-a")

    assert result["status"] == "FAILED"
    assert "duplicate_fact_rows" in result["blocking_errors"]


def test_quality_gate_accepts_consistent_gold_row():
    fact = pd.DataFrame(
        [{"item_id": "a", "kode_iku": "IKU-1", "jumlah": 100, "allocation_weight": 1, "jumlah_weighted_iku": 100, "dataset_session_id": "dataset-a", "run_id": "run-a", "tahun": "2025", "prodi": "SD", "kegiatan": "K", "uraian_detail": "U", "source_file": "x.xlsx", "source_sheet": "RAB", "source_row": 2, "created_at": "2026-01-01T00:00:00+00:00"}]
    )

    assert evaluate_gold_quality(fact, "dataset-a", "run-a")["status"] == "PASSED"
