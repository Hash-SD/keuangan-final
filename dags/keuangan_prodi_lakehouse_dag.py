from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


PY = "python"

with DAG(
    dag_id="keuangan_prodi_lakehouse_dag",
    start_date=datetime(2026, 5, 26),
    schedule=None,
    catchup=False,
    tags=["lakehouse", "keuangan", "medallion"],
) as dag:
    start = EmptyOperator(task_id="start")
    generate_dummy_data = BashOperator(task_id="generate_dummy_data", bash_command=f"{PY} /opt/airflow/src/generators/generate_all.py")
    quality_gate_process = BashOperator(task_id="quality_gate_process", bash_command=f"{PY} /opt/airflow/src/validation/quality_gate.py")
    extract_bronze = BashOperator(task_id="extract_bronze", bash_command=f"{PY} /opt/airflow/src/transformations/bronze_ingest.py")
    clean_silver = BashOperator(task_id="clean_silver", bash_command=f"{PY} /opt/airflow/src/transformations/silver_clean.py")
    load_gold_schema = BashOperator(task_id="load_gold_schema", bash_command=f"{PY} /opt/airflow/src/transformations/gold_star_schema.py")
    validate_mart = BashOperator(task_id="validate_mart", bash_command=f"{PY} /opt/airflow/src/metrics/reconcile_control_total.py")
    calculate_metrics = BashOperator(
        task_id="calculate_metrics",
        bash_command=(
            f"{PY} /opt/airflow/src/metrics/pipeline_latency.py && "
            f"{PY} /opt/airflow/src/metrics/data_freshness.py && "
            f"{PY} /opt/airflow/src/metrics/dropout_rate.py && "
            f"{PY} /opt/airflow/src/metrics/data_quality_score.py && "
            f"{PY} /opt/airflow/src/metrics/generate_uat.py"
        ),
    )
    refresh_superset_dataset = BashOperator(task_id="refresh_superset_dataset", bash_command="echo Superset dataset refresh documented in src/sql/superset_datasets.sql")
    end = EmptyOperator(task_id="end")

    start >> generate_dummy_data >> quality_gate_process >> extract_bronze >> clean_silver >> load_gold_schema >> validate_mart >> calculate_metrics >> refresh_superset_dataset >> end

