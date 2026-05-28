# CHECKPOINT-AUDIT-01: Docker Inventory

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
docker compose ps
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker compose config --services
docker compose config
```

## Compose Project

```text
name: keuangan-final
network: lakehouse_net
```

## Service Utama Yang Harus Running

| Container | Service | Image | Status | Port Mapping | Fungsi |
|---|---|---|---|---|---|
| `keuangan-postgres-metastore` | `postgres-metastore` | `postgres:16-alpine` | Up healthy | `5432:5432` | PostgreSQL metastore dan fallback gold tables |
| `keuangan-minio` | `minio` | `minio/minio:latest` | Up healthy | `9000:9000`, `9001:9001` | Object storage API dan console |
| `keuangan-spark-master` | `spark-master` | `apache/spark:3.5.6` | Up healthy | `8080:8080`, `7077:7077` | Spark standalone master UI dan RPC |
| `keuangan-spark-worker` | `spark-worker` | `apache/spark:3.5.6` | Up | `8081:8081` | Spark standalone worker |
| `keuangan-airflow-webserver` | `airflow-webserver` | `apache/airflow:2.10.5-python3.11` | Up healthy | `8085:8080` | Airflow UI/API webserver |
| `keuangan-airflow-scheduler` | `airflow-scheduler` | `apache/airflow:2.10.5-python3.11` | Up | internal `8080/tcp`, no host publish | Airflow scheduler |
| `keuangan-trino` | `trino` | `trinodb/trino:474` | Up healthy | `8082:8080` | Trino SQL engine |
| `keuangan-superset` | `superset` | `apache/superset:4.1.1` | Up healthy | `8089:8088` | BI dashboard |

## Service Init-Only Yang Boleh Exited

| Container | Service | Image | Status | Fungsi | Audit |
|---|---|---|---|---|---|
| `keuangan-airflow-init` | `airflow-init` | `apache/airflow:2.10.5-python3.11` | Exited (0) | Migrasi DB Airflow dan create admin user | OK bila exit code 0 |
| `keuangan-minio-init` | `minio-init` | `minio/mc:latest` | Exited (0) | Setup alias dan bucket `lakehouse` | OK bila exit code 0 |

## Compose Services

```text
postgres-metastore
airflow-init
airflow-scheduler
airflow-webserver
minio
trino
superset
minio-init
spark-master
spark-worker
```

## Catatan Penting

- `airflow-init` dan `minio-init` memang one-shot init service. Status `Exited (0)` tidak dianggap error.
- Service utama yang perlu berjalan terus adalah PostgreSQL, MinIO, Spark master/worker, Airflow webserver/scheduler, Trino, dan Superset.
- Airflow scheduler menampilkan internal `8080/tcp` tanpa host port. Itu bukan konflik host karena tidak dipublish.

## Acceptance

- Semua container terdaftar: PASS.
- Init container dibedakan dari service utama: PASS.
- Tidak ada kesimpulan salah bahwa init container harus running terus: PASS.
