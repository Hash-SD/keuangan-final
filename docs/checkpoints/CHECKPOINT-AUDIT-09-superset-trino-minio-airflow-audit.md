# CHECKPOINT-AUDIT-09: Superset Trino MinIO Airflow Audit

Tanggal: 2026-05-28
Status: Selesai

## Airflow

Health:

```text
GET http://localhost:8085/health -> HTTP 200
```

DAG list:

```text
dag_id                       | fileloc                                           | owners  | is_paused
keuangan_prodi_lakehouse_dag | /opt/airflow/dags/keuangan_prodi_lakehouse_dag.py | airflow | False
```

Scheduler:

```text
airflow jobs check --job-type SchedulerJob -> Found one alive job.
```

Catatan: `keuangan-airflow-init` tetap `Exited (0)` dan tidak dianggap error.

## Superset

Health:

```text
GET http://localhost:8089/health -> HTTP 200 OK
```

Assets:

```json
{
  "database_id": 2,
  "dataset_id": 1,
  "database_name": "Trino Iceberg Gold Keuangan",
  "table_name": "vw_dashboard_piutang_ukt"
}
```

Dashboard:

```json
{
  "dashboard_id": 1,
  "dashboard_title": "Dashboard Piutang UKT Prodi",
  "dashboard_url": "http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/",
  "chart_ids": [1, 2, 3, 4, 5, 6]
}
```

Credential:

```text
admin / admin
```

## Trino

Info endpoint:

```text
GET http://localhost:8082/v1/info -> HTTP 200
version=474
```

Gold query:

```sql
SELECT SUM(f.nominal_piutang_rp), COUNT(*)
FROM fact_piutang_ukt_prodi f
JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key
WHERE o.nama_prodi = 'Sains Data';
```

Hasil:

```text
"31250000","15"
```

Catatan nonfatal:

```text
WARNING: Unable to create a system terminal, creating a dumb terminal
```

## MinIO

Console:

```text
http://localhost:9001
```

Credential:

```text
minioadmin / minioadmin
```

Bucket:

```text
local/lakehouse/
```

Init container `keuangan-minio-init` `Exited (0)` dan bucket sudah tersedia.

## Spark

Spark Master UI:

```text
GET http://localhost:8080 -> HTTP 200
ContainsSparkMaster=True
```

Spark Worker UI:

```text
GET http://localhost:8081 -> HTTP 200
ContainsWorker=True
ContainsSpark=True
```

Spark Master RPC:

```text
localhost:7077 -> TCP OK
```

## PostgreSQL

TCP:

```text
localhost:5432 -> TCP OK
```

Query:

```sql
SELECT COUNT(*) AS fact_rows, SUM(nominal_piutang_rp) AS total_piutang
FROM gold.fact_piutang_ukt_prodi;
```

Hasil:

```text
fact_rows=803
total_piutang=1955550000
```

## Acceptance

- Airflow bisa dibuka dan DAG terdeteksi: PASS.
- Airflow scheduler running: PASS.
- Superset health OK dan dashboard asset tercatat: PASS.
- Trino info endpoint OK dan query Gold berhasil: PASS.
- MinIO console/API OK dan bucket `lakehouse` tersedia: PASS.
- Spark master/worker UI OK: PASS.
- PostgreSQL TCP dan query OK: PASS.
- Tidak ada port salah: PASS.
