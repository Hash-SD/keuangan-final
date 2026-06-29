from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


AIRFLOW_AVAILABLE = importlib.util.find_spec("airflow") is not None


@pytest.mark.skipif(not AIRFLOW_AVAILABLE, reason="airflow is not installed in local test environment")
def test_excel_lakehouse_dag_imports_and_has_final_tasks():
    import dags.keuangan_prodi_excel_lakehouse_dag as dag_module

    dag = dag_module.dag
    task_ids = set(dag.task_ids)

    assert "extract_excel_to_bronze" in task_ids
    assert "write_minio_storage" in task_ids
    assert "load_gold_to_postgres" in task_ids
    assert "load_gold_to_iceberg" in task_ids
    assert "refresh_superset_dashboard" in task_ids
    assert "generate_system_status" in task_ids
