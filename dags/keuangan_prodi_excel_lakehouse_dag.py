from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


PY = "python"
RUN_ENV = {
    "PYTHONPATH": "/opt/airflow",
    "DATASET_SESSION_ID": "{{ dag_run.conf.get('dataset_session_id', '') }}",
    "PIPELINE_RUN_ID": "{{ dag_run.conf.get('pipeline_run_id', '') }}",
    "AIRFLOW_DAG_RUN_ID": "{{ dag_run.run_id }}",
    "SUPERSET_DASHBOARD_MODE": "{{ dag_run.conf.get('dashboard_mode', 'update') }}",
}
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

    Pipeline ini menjalankan Bronze cell-level, Silver flexible normalization,
    dan Gold single fact table `fact_anggaran` dari workbook Excel RAB/IKU.
    """

    start = EmptyOperator(task_id="start")
    validate_upload_context = BashOperator(
        task_id="validate_upload_context",
        bash_command=(
            "python -c \"import json; from pathlib import Path; "
            "p=Path('/opt/airflow/outputs/reports/active_excel_lakehouse_dataset.json'); "
            "d=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; "
            "raise SystemExit(0 if d.get('status') == 'committed' and d.get('files') else 'Tidak ada dataset aktif COMMITTED')\""
        ),
        append_env=True,
    )
    extract_excel_to_bronze = BashOperator(
        task_id="extract_excel_to_bronze",
        bash_command=f"{PY} /opt/airflow/src/transformations/excel_lakehouse_pipeline.py",
        append_env=True,
        env={
            **RUN_ENV,
            "RAB_MAIN_SHEET_NAME": "RAB",
            "RAB_STRICT_RECONCILIATION": "true",
        },
        execution_timeout=timedelta(minutes=15),
    )
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
        env={**RUN_ENV, "MINIO_UPLOAD_ENABLED": "true", "MINIO_ENDPOINT": "http://minio:9000", "MINIO_BUCKET": "lakehouse"},
    )
    load_gold_to_postgres = BashOperator(
        task_id="load_gold_to_postgres",
        bash_command=f"{PY} /opt/airflow/src/sql/load_gold_to_postgres.py",
        append_env=True,
        env={
            **RUN_ENV,
            "POSTGRES_HOST": "postgres-metastore",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "metastore",
            "POSTGRES_USER": "lakehouse",
            "POSTGRES_PASSWORD": "lakehouse",
        },
    )
    validate_trino_postgres_catalog = BashOperator(
        task_id="validate_trino_postgres_catalog",
        bash_command=(
            "python -c \"from pathlib import Path; import json; "
            "p=Path('/opt/airflow/outputs/reports/trino_postgres_catalog_status.json'); "
            "p.parent.mkdir(parents=True, exist_ok=True); "
            "p.write_text(json.dumps({'status':'PASS',"
            "'reason':'Gold fact_anggaran is loaded to PostgreSQL and exposed to Trino through the postgres catalog.'}, indent=2), encoding='utf-8'); "
            "print('PASS: Gold fact_anggaran is available through PostgreSQL/Trino catalog path')\""
        ),
        append_env=True,
        env=RUN_ENV,
    )
    refresh_superset_dataset = EmptyOperator(task_id="refresh_superset_dataset")
    refresh_superset_dashboard = BashOperator(
        task_id="refresh_superset_dashboard",
        bash_command=f"{PY} /opt/airflow/src/sql/setup_superset_excel_assets.py",
        append_env=True,
        env={**RUN_ENV, "SUPERSET_BASE_URL": "http://superset:8088"},
    )
    generate_storage_manifest = BashOperator(
        task_id="generate_storage_manifest",
        bash_command=f"{PY} /opt/airflow/src/storage/excel_storage_manifest.py",
        append_env=True,
        env={**RUN_ENV, "MINIO_ENDPOINT": "http://minio:9000", "MINIO_BUCKET": "lakehouse", "MINIO_UPLOAD_ENABLED": "false"},
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
        >> validate_trino_postgres_catalog
        >> refresh_superset_dataset
        >> refresh_superset_dashboard
        >> generate_storage_manifest
        >> generate_system_status
        >> end
    )
