from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


PY = "python"
DEFAULT_ARGS = {
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="keuangan_prodi_lakehouse_dag",
    start_date=datetime(2026, 5, 26),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["lakehouse", "keuangan", "medallion"],
) as dag:
    dag.doc_md = """
    Pipeline end-to-end Data Lakehouse Keuangan Prodi.

    Semua task bersifat idempotent: output ditulis ulang secara deterministik
    berdasarkan batch dummy yang sama sehingga aman saat Airflow melakukan retry.
    """
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
    load_gold_postgres_fallback = BashOperator(
        task_id="load_gold_postgres_fallback",
        bash_command=f"{PY} /opt/airflow/src/sql/load_gold_to_postgres.py",
        env={
            "POSTGRES_HOST": "postgres-metastore",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "metastore",
            "POSTGRES_USER": "lakehouse",
            "POSTGRES_PASSWORD": "lakehouse",
            "PYTHONPATH": "/opt/airflow",
        },
    )
    refresh_superset_dataset = BashOperator(
        task_id="refresh_superset_dataset",
        bash_command=f"{PY} /opt/airflow/src/sql/setup_superset_assets.py",
        env={
            "SUPERSET_BASE_URL": "http://superset:8088",
            "PYTHONPATH": "/opt/airflow",
        },
    )
    refresh_superset_dashboard = BashOperator(
        task_id="refresh_superset_dashboard",
        bash_command=f"{PY} /opt/airflow/src/sql/setup_superset_dashboard.py",
        env={
            "SUPERSET_BASE_URL": "http://superset:8088",
            "PYTHONPATH": "/opt/airflow",
        },
    )
    end = EmptyOperator(task_id="end")

    start >> generate_dummy_data >> quality_gate_process >> extract_bronze >> clean_silver >> load_gold_schema >> validate_mart >> calculate_metrics >> load_gold_postgres_fallback >> refresh_superset_dataset >> refresh_superset_dashboard >> end
