from __future__ import annotations

import json

import pytest

from src.sql import load_gold_to_postgres


def test_failed_active_gold_run_cannot_be_loaded_to_postgres(tmp_path, monkeypatch):
    reports = tmp_path / "outputs/reports"
    reports.mkdir(parents=True)
    (reports / "active_gold_run.json").write_text(
        json.dumps({
            "status": "failed",
            "dataset_session_id": "dataset-1",
            "pipeline_run_id": "run-1",
            "outputs": {"fact_anggaran.csv": {"csv": "data/fact.csv"}},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(load_gold_to_postgres, "OUTPUTS_DIR", tmp_path / "outputs")

    with pytest.raises(RuntimeError, match="Gold aktif belum berstatus PUBLISHED"):
        load_gold_to_postgres._active_run_outputs("run-1", "dataset-1")


def test_sql_identifier_guard_rejects_path_and_statement_injection():
    with pytest.raises(ValueError):
        load_gold_to_postgres._safe_sql_identifier("run-1; DROP SCHEMA gold")
    assert load_gold_to_postgres._safe_sql_identifier("run-1") == "run1"
