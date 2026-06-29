# FINAL VERIFICATION REPORT

Final status: `PARTIAL`

Zero critical error verified: `NO`

## Ringkasan

Clean local Excel Lakehouse pipeline berhasil dari lima file Excel nyata dan menghasilkan counts target: Bronze 55340, Silver RAB 445, Nomenklatur 248, fact_anggaran 445. Data Gold berhasil dimuat ke PostgreSQL dan dibaca Trino via postgres catalog. MinIO manifest terbaru berstatus uploaded.

## Data Input

- RAB 2025 SD RAB IKU.xlsx
- Nomenklatur.xlsx
- Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx
- RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx
- RAB_SD_Usulan KE (1)_jul-des 2023.xlsx

## Evidence Utama

- Pipeline: `outputs/evidence/pipeline_clean_run_output.txt`
- Counts: `outputs/evidence/pipeline_counts.json`
- Parquet: `outputs/evidence/parquet_counts.json`
- Fact totals: `outputs/evidence/fact_anggaran_totals.json`
- MinIO: `outputs/evidence/minio_objects.txt`
- Postgres: `outputs/evidence/postgres_query_raw.txt`
- Trino: `outputs/evidence/trino_count_raw.txt`
- Airflow: `outputs/evidence/airflow_dag_run.txt`
- Backend upload: `outputs/evidence/backend_api_check.json`
- Portal screenshot: `outputs/evidence/portal_screenshots/portal_home.png`

## Known Limitations

- Airflow is PARTIAL: CLI trigger works and one DAG run succeeded with Iceberg skipped, but sample-file run is stuck running/zombie at `extract_excel_to_bronze`.
- Iceberg is `SKIPPED_WITH_REASON`: PySpark/Iceberg runtime is not installed in the Airflow task image.
- Future 2026 test failed: parser still emits 2025 when using 2025 workbook copy with metadata 2026.
- Superset is PARTIAL: health/assets checked, but full dashboard chart parity was not proven.
- Frontend is PARTIAL: portal opens, but Playwright upload specs fail waiting for expected heading.
- Tests are FAIL overall: pytest has 70 passed, 1 skipped, 1 teardown error; npm test is placeholder failure; Playwright has 3 failures.

## Final Status

`PARTIAL`
