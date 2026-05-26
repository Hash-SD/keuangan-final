# Production Readiness Notes

Dokumen ini mencatat hasil audit ulang berbasis `find-skills`, Context7, dan validasi lokal.

## Skill Basis

Skill discovery dilakukan dengan `npx skills find` untuk:

- production readiness Python data pipeline
- Python cleanup/testing/dependencies
- Apache Airflow production DAG
- Docker Compose healthcheck

Skill yang paling kuat dan relevan:

- `wshobson/agents@airflow-dag-patterns` dengan 6.8K installs.
- `jeffallan/claude-skills@spark-engineer` untuk Spark/data processing.
- `hamelsmu/evals-skills@generate-synthetic-data` untuk data dummy.

Kandidat Docker production dan deploying Airflow ditemukan, tetapi install count di bawah 1K, sehingga dipakai sebagai sinyal pencarian saja. Keputusan teknis mengikuti dokumentasi resmi melalui Context7.

## Context7 Basis

Dokumentasi resmi dicek ulang untuk:

- Docker Compose: healthcheck, `depends_on`, restart policy, volumes, environment.
- Apache Airflow: idempotent task, retry, dependency chain, `catchup=False`.
- Apache Iceberg: Spark catalog, JDBC metastore, S3/MinIO warehouse.
- Trino: Iceberg connector catalog dan query validasi.
- Apache Superset: API database/dataset, access token, CSRF token.

## Hardening yang Dilakukan

- Docker service long-running memakai `restart: unless-stopped`.
- Spark healthcheck memakai Spark UI lokal yang benar-benar tersedia di image.
- Airflow DAG memakai retry, retry delay, `max_active_runs=1`, dan dokumentasi DAG.
- Dependency runtime ditulis eksplisit di `requirements.txt`.
- `.dockerignore` ditambahkan agar build context tidak membawa output/generated/cache.
- Full run Windows disediakan di `scripts/full_run.ps1` karena `make` tidak tersedia di environment ini.
- Superset connection dan dataset dibuat via API, bukan hanya instruksi manual.
- Gold utama dimuat ke Iceberg catalog penuh di MinIO; PostgreSQL `gold` hanya fallback kompatibilitas.
- Port lokal divalidasi dengan `scripts/check_ports.ps1`.

## Validasi Wajib Sebelum Push

```powershell
python -m compileall src dags tests
docker compose config
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\full_run.ps1
python -m pytest tests -v
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_ports.ps1
```

Expected:

- Python compile: no error.
- Compose config: valid.
- Full run: selesai tanpa error.
- Tests: `6 passed`.
- Spark Iceberg load: 6 tabel Gold tertulis ke `s3://lakehouse/warehouse/gold`.
- Trino Iceberg: `"31250000","15"`.
- Port lokal: semua OK.

## Catatan Produksi Nyata

Untuk production sungguhan, ganti nilai default secret di `.env.example`, gunakan secret manager, pisahkan database Airflow dari metastore data, dan gunakan object storage/metastore terkelola untuk Iceberg.
