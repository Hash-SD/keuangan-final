# CHECKPOINT-AUDIT-04: Service Healthcheck

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_ports.ps1
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:9001" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8081" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8085/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8082/v1/info" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8089/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8090" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8091/api/health" -UseBasicParsing
Test-NetConnection -ComputerName localhost -Port 5432
Test-NetConnection -ComputerName localhost -Port 7077
```

## check_ports.ps1

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

## Manual HTTP Check

```text
OK 200 http://localhost:9000/minio/health/live
OK 200 http://localhost:9001
OK 200 http://localhost:8080
OK 200 http://localhost:8081
OK 200 http://localhost:8085/health
OK 200 http://localhost:8082/v1/info
OK 200 http://localhost:8089/health
OK 200 http://localhost:8090
OK 200 http://localhost:8091/api/health
```

## Manual TCP Check

```text
localhost:5432 TcpTestSucceeded=True
localhost:7077 TcpTestSucceeded=True
```

## Docker Status

Service utama:

```text
keuangan-airflow-scheduler    Up
keuangan-airflow-webserver    Up (healthy)
keuangan-minio                Up (healthy)
keuangan-postgres-metastore   Up (healthy)
keuangan-spark-master         Up (healthy)
keuangan-spark-worker         Up
keuangan-superset             Up (healthy)
keuangan-trino                Up (healthy)
```

## Acceptance

- Semua service utama online: PASS.
- `check_ports.ps1` memakai port final dan lolos: PASS.
- Backend API ikut dicek: PASS.
- Tidak ada false positive pada manual HTTP/TCP checks: PASS.
