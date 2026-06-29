from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


PY = "python"
DEFAULT_ARGS = {
    "owner": "data-team",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


with DAG(
    dag_id="keuangan_prodi_excel_lakehouse_dag",
    start_date=datetime(2026, 6, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["lakehouse", "keuangan", "excel", "rab", "iku"],
) as dag:
    dag.doc_md = """
    SILARAS SD - Sistem Lakehouse Anggaran RAB dan IKU Sains Data.

    Pipeline ini mengganti domain lama PDF/piutang menjadi Bronze cell-level,
    Silver flexible normalization, dan Gold single fact table `fact_anggaran`.
    """

    start = EmptyOperator(task_id="start")
    validate_upload_context = BashOperator(task_id="validate_upload_context", bash_command="test -d /opt/airflow/data/raw/excel")
    extract_excel_to_bronze = BashOperator(task_id="extract_excel_to_bronze", bash_command=f"{PY} /opt/airflow/src/transformations/excel_lakehouse_pipeline.py")
    detect_year_and_format = EmptyOperator(task_id="detect_year_and_format")
    parse_flexible = EmptyOperator(task_id="parse_flexible")
    merge_multi_file = EmptyOperator(task_id="merge_multi_file")
    normalize_silver = EmptyOperator(task_id="normalize_silver")
    map_iku_and_nomenklatur = EmptyOperator(task_id="map_iku_and_nomenklatur")
    validate_excel_totals = EmptyOperator(task_id="validate_excel_totals")
    build_fact_anggaran = EmptyOperator(task_id="build_fact_anggaran")
    write_minio_storage = BashOperator(
        task_id="write_minio_storage",
        bash_command=f"{PY} /opt/airflow/src/storage/excel_storage_manifest.py",
        append_env=True,
        env={"PYTHONPATH": "/opt/airflow", "MINIO_UPLOAD_ENABLED": "true", "MINIO_ENDPOINT": "http://minio:9000", "MINIO_BUCKET": "lakehouse"},
    )
    load_gold_to_postgres = BashOperator(
        task_id="load_gold_to_postgres",
        bash_command=f"{PY} /opt/airflow/src/sql/load_gold_to_postgres.py",
        append_env=True,
        env={
            "POSTGRES_HOST": "postgres-metastore",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "metastore",
            "POSTGRES_USER": "lakehouse",
            "POSTGRES_PASSWORD": "lakehouse",
            "PYTHONPATH": "/opt/airflow",
        },
    )
    load_gold_to_iceberg = BashOperator(
        task_id="load_gold_to_iceberg",
        bash_command=f"{PY} /opt/airflow/src/transformations/load_gold_iceberg.py",
        append_env=True,
        env={"PYTHONPATH": "/opt/airflow", "MINIO_ENDPOINT": "http://minio:9000", "MINIO_BUCKET": "lakehouse"},
    )
    refresh_superset_dataset = EmptyOperator(task_id="refresh_superset_dataset")
    refresh_superset_dashboard = BashOperator(
        task_id="refresh_superset_dashboard",
        bash_command=f"{PY} /opt/airflow/src/sql/setup_superset_excel_assets.py",
        append_env=True,
        env={"SUPERSET_BASE_URL": "http://superset:8088", "PYTHONPATH": "/opt/airflow"},
    )
    generate_storage_manifest = BashOperator(
        task_id="generate_storage_manifest",
        bash_command=f"{PY} /opt/airflow/src/storage/excel_storage_manifest.py",
        append_env=True,
        env={"PYTHONPATH": "/opt/airflow", "MINIO_ENDPOINT": "http://minio:9000", "MINIO_BUCKET": "lakehouse", "MINIO_UPLOAD_ENABLED": "false"},
    )
    generate_system_status = BashOperator(task_id="generate_system_status", bash_command=f"{PY} /opt/airflow/src/status/system_truth_status.py")
    end = EmptyOperator(task_id="end")

    (
        start
        >> validate_upload_context
        >> extract_excel_to_bronze
        >> detect_year_and_format
        >> parse_flexible
        >> merge_multi_file
        >> normalize_silver
        >> map_iku_and_nomenklatur
        >> validate_excel_totals
        >> build_fact_anggaran
        >> write_minio_storage
        >> load_gold_to_postgres
        >> load_gold_to_iceberg
        >> refresh_superset_dataset
        >> refresh_superset_dashboard
        >> generate_storage_manifest
        >> generate_system_status
        >> end
    )
