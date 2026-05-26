# CHECKPOINT-09: Final Run

## Ringkasan

Final run end-to-end berhasil dijalankan secara lokal dan melalui Airflow. Docker stack utama berjalan healthy, DAG Airflow sukses, Gold mart dapat divalidasi oleh Trino, dan test utama lulus.

## Command Final

```powershell
python src/generators/generate_all.py
python src/validation/quality_gate.py
python src/transformations/bronze_ingest.py
python src/transformations/silver_clean.py
python src/transformations/gold_star_schema.py
python src/metrics/reconcile_control_total.py
python src/metrics/pipeline_latency.py
python src/metrics/data_freshness.py
python src/metrics/dropout_rate.py
python src/metrics/data_quality_score.py
python src/metrics/generate_uat.py
python src/sql/load_gold_to_postgres.py
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
python src/sql/setup_superset_assets.py
python -m pytest tests -v
```

## Docker Service

Service aktif:

- MinIO
- PostgreSQL metastore
- Spark master
- Spark worker
- Airflow webserver
- Airflow scheduler
- Trino
- Superset

## Validasi Akhir

- Total piutang Sains Data: 31250000.
- Jumlah penunggak Sains Data: 15.
- Total RAB: 150000000.
- Dropout rate: 2.0%.
- Data quality score: 100.0.
- Airflow DAG run sukses: `manual__2026-05-26T09:20:28+00:00`.
- Airflow DAG run ulang setelah hardening sukses: `manual__2026-05-26T09:42:32+00:00`.
- Trino Iceberg query result: `"31250000","15"`.
- Superset database/dataset API setup: database_id 2, dataset_id 1.
- Port lokal: semua OK via `scripts/check_ports.ps1`.
- Test result: `6 passed`.

## Audit Production Readiness

Audit ulang dilakukan dengan:

```powershell
npx skills find "production readiness python data pipeline testing docker airflow"
npx skills find "python project cleanup tests dependencies best practices"
npx skills find "apache airflow production dag best practices"
npx skills find "docker compose production readiness healthcheck"
python -m compileall src dags tests
docker compose config
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\full_run.ps1
python -m pytest tests -v
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
```

Perubahan hardening:

- Airflow DAG memakai retry, retry delay, `max_active_runs=1`, dan task idempotent.
- Docker Compose service long-running memakai `restart: unless-stopped`.
- Superset asset setup memiliki retry/wait terhadap API agar tidak race dengan startup container.
- Gold utama sudah pindah ke Iceberg catalog penuh di MinIO.
- Script validasi port lokal ditambahkan.
- Dependency `requests` dan `psycopg2-binary` ditulis eksplisit.
- `.dockerignore` ditambahkan.
- Catatan produksi tersedia di `docs/production-readiness.md`.

## Status

End-to-end runnable selesai.
