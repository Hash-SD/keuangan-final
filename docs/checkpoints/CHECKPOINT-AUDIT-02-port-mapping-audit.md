# CHECKPOINT-AUDIT-02: Port Mapping Audit

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
docker compose ps
docker port keuangan-trino
docker port keuangan-airflow-webserver
docker port keuangan-superset
docker port keuangan-minio
docker port keuangan-spark-master
docker port keuangan-spark-worker
docker port keuangan-postgres-metastore
```

## Tabel Port Final

| Service | Container Port | Host Port | URL / Akses Pengguna | Status |
|---|---:|---:|---|---|
| PostgreSQL metastore | 5432 | 5432 | `localhost:5432` | TCP, bukan browser |
| MinIO API | 9000 | 9000 | `http://localhost:9000/minio/health/live` | HTTP 200 |
| MinIO Console | 9001 | 9001 | `http://localhost:9001` | HTTP 200 |
| Spark Master UI | 8080 | 8080 | `http://localhost:8080` | HTTP 200 |
| Spark Master RPC | 7077 | 7077 | `localhost:7077` / `spark://localhost:7077` | TCP OK |
| Spark Worker UI | 8081 | 8081 | `http://localhost:8081` | HTTP 200 |
| Airflow Webserver | 8080 | 8085 | `http://localhost:8085`, health `http://localhost:8085/health` | HTTP 200 |
| Trino | 8080 | 8082 | `http://localhost:8082/v1/info` | HTTP 200 |
| Superset | 8088 | 8089 | `http://localhost:8089`, health `http://localhost:8089/health` | HTTP 200 |
| Portal Frontend | local process | 8090 | `http://localhost:8090` | HTTP 200 |
| Portal Backend | local process | 8091 | `http://localhost:8091/api/health` | HTTP 200 |

## Docker Port Output

```text
keuangan-trino:              8080/tcp -> 0.0.0.0:8082
keuangan-airflow-webserver:  8080/tcp -> 0.0.0.0:8085
keuangan-superset:           8088/tcp -> 0.0.0.0:8089
keuangan-minio:              9000/tcp -> 0.0.0.0:9000, 9001/tcp -> 0.0.0.0:9001
keuangan-spark-master:       7077/tcp -> 0.0.0.0:7077, 8080/tcp -> 0.0.0.0:8080
keuangan-spark-worker:       8081/tcp -> 0.0.0.0:8081
keuangan-postgres-metastore: 5432/tcp -> 0.0.0.0:5432
```

## Perbaikan Yang Dilakukan

File diperbarui agar host port dan container port tidak tercampur:

- `README.md`
  - Menambahkan backend API `http://localhost:8091/api/health`.
  - Menjelaskan MinIO API health `http://localhost:9000/minio/health/live`.
  - Menambahkan Spark Master RPC `localhost:7077`.
  - Mengganti Trino menjadi `http://localhost:8082/v1/info`.
  - Menambahkan Superset health `http://localhost:8089/health`.
  - Menambahkan PostgreSQL metastore `localhost:5432`.

- `scripts/check_ports.ps1`
  - Menambahkan health check Portal Backend API di `http://localhost:8091/api/health`.

- `portal_backend/services/system_status.py`
  - MinIO API diarahkan ke health endpoint host port `9000`.
  - Menambahkan `Spark Master RPC` sebagai TCP service `localhost:7077`.

- `portal/index.html`
  - System page memisahkan MinIO API `9000` dan MinIO Console `9001`.
  - System page memisahkan Spark Master UI `8080` dan Spark Master RPC `7077`.
  - PostgreSQL tetap memakai `Copy Connection`.

Backend direstart agar perubahan status service terbaru aktif.

## Verifikasi

`scripts/check_ports.ps1` setelah perbaikan:

```text
OK TCP  PostgreSQL metastore localhost:5432
OK HTTP MinIO API http://localhost:9000/minio/health/live -> 200
OK HTTP MinIO Console http://localhost:9001 -> 200
OK HTTP Spark Master UI http://localhost:8080 -> 200
OK HTTP Spark Worker UI http://localhost:8081 -> 200
OK TCP  Spark Master RPC localhost:7077
OK HTTP Airflow Webserver http://localhost:8085/health -> 200
OK HTTP Trino http://localhost:8082/v1/info -> 200
OK HTTP Superset http://localhost:8089/health -> 200
OK HTTP Portal Lokal http://localhost:8090 -> 200
OK HTTP Portal Backend API http://localhost:8091/api/health -> 200
```

Search untuk port keliru di README/UI/backend/scripts:

```text
localhost:8088: tidak ditemukan
localhost:8080/v1/info: tidak ditemukan
http://localhost:8088: tidak ditemukan
```

## Acceptance

- Semua port jelas: PASS.
- Tidak ada port duplicate yang membingungkan di URL pengguna: PASS.
- URL pengguna memakai host port: PASS.
- PostgreSQL tidak dibuat sebagai link browser: PASS.
- README, Portal System Page, backend service status, dan check script memakai host port: PASS.
