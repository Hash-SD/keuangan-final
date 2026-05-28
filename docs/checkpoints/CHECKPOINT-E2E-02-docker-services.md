# CHECKPOINT-E2E-02 - Docker Services

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d
docker compose ps
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_portal.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_ports.ps1
```

## Docker Compose

`docker compose up -d` berhasil menjalankan service. Status akhir `docker compose ps`:

```text
keuangan-airflow-scheduler    Up
keuangan-airflow-webserver    Up (healthy)   0.0.0.0:8085->8080/tcp
keuangan-minio                Up (healthy)   0.0.0.0:9000-9001->9000-9001/tcp
keuangan-postgres-metastore   Up (healthy)   0.0.0.0:5432->5432/tcp
keuangan-spark-master         Up (healthy)   0.0.0.0:7077->7077/tcp, 0.0.0.0:8080->8080/tcp
keuangan-spark-worker         Up             0.0.0.0:8081->8081/tcp
keuangan-superset             Up (healthy)   0.0.0.0:8089->8088/tcp
keuangan-trino                Up (healthy)   0.0.0.0:8082->8080/tcp
```

Portal lokal berhasil dijalankan:

```text
Portal lokal aktif: http://localhost:8090
```

## Port Check

`scripts/check_ports.ps1` berhasil:

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
```

## Acceptance

- Semua container penting running: PASS.
- Health service wajib online: PASS.
- `scripts/check_ports.ps1` lolos: PASS.
- Portal lokal aktif: PASS.
- Tidak ada perbaikan port/config yang diperlukan pada checkpoint ini.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-03-data-generation.md`.
