from __future__ import annotations

import os

import pytest

from src.transformations import excel_lakehouse_pipeline


def test_production_rejects_pipeline_without_committed_dataset(monkeypatch, tmp_path):
    monkeypatch.delenv("ALLOW_SAMPLE_DATA", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(excel_lakehouse_pipeline, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "missing.json")

    with pytest.raises(ValueError, match="dataset aktif"):
        excel_lakehouse_pipeline.discover_excel_sources()


def test_airflow_dag_has_no_sample_excel_fallback():
    dag_text = open("dags/keuangan_prodi_excel_lakehouse_dag.py", encoding="utf-8").read()

    assert "SAMPLE_EXCEL_DIR" not in dag_text
    assert "FINANCE_EXCEL_FILES is empty" not in dag_text
