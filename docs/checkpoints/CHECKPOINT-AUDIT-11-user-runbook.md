# CHECKPOINT-AUDIT-11: User Runbook

Tanggal: 2026-05-28
Status: Selesai

## 1. Cara Menjalankan Docker

```powershell
cd C:\Users\hm\keuangan-final
docker compose up -d
```

## 2. Cara Cek Container

```powershell
docker compose ps
docker ps -a
```

Service utama harus `Up`:

```text
keuangan-postgres-metastore
keuangan-minio
keuangan-spark-master
keuangan-spark-worker
keuangan-airflow-webserver
keuangan-airflow-scheduler
keuangan-trino
keuangan-superset
```

Init container boleh `Exited (0)`:

```text
keuangan-airflow-init
keuangan-minio-init
```

## 3. Cara Menjalankan Portal

```powershell
.\scripts\start_portal.ps1
```

Portal:

```text
http://localhost:8090
```

## 4. Cara Menjalankan Backend

```powershell
.\scripts\start_portal_backend.ps1
```

Backend health:

```text
http://localhost:8091/api/health
```

## 5. Cara Cek Port

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_ports.ps1
```

Expected:

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

## 6. URL Pengguna

```text
Portal:          http://localhost:8090
Backend:         http://localhost:8091/api/health
Airflow:         http://localhost:8085
Superset:        http://localhost:8089
Superset dash:   http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/
MinIO API:       http://localhost:9000/minio/health/live
MinIO Console:   http://localhost:9001
Spark Master:    http://localhost:8080
Spark Worker:    http://localhost:8081
Spark RPC:       localhost:7077
Trino:           http://localhost:8082/v1/info
PostgreSQL:      localhost:5432
```

Credential:

```text
Airflow:    airflow / airflow
Superset:   admin / admin
MinIO:      minioadmin / minioadmin
PostgreSQL: lakehouse / lakehouse, database metastore
```

## 7. Urutan Uji Coba Pengguna

1. Buka `http://localhost:8090`.
2. Buka halaman `System`.
3. Cek semua service berstatus online.
4. Buka halaman `Data`.
5. Cek PDF/CSV/Excel berstatus ready.
6. Buka halaman `Orkestrasi`.
7. Klik `Run Quality Gate`.
8. Klik `Run Bronze`.
9. Klik `Run Silver`.
10. Klik `Run Gold`.
11. Klik `Validate Gold`.
12. Klik `Full Run Basic`.
13. Buka halaman `Dashboard`.
14. Cek metrics.
15. Buka halaman `Lakehouse`.
16. Cek Bronze/Silver/Gold ready dan Gold Validation PASS.
17. Buka halaman `Analytics`.
18. Klik `Submit UAT dummy`.
19. Buka Superset Dashboard.

## 8. Expected Result

```text
Total Piutang UKT: Rp31.250.000
Mahasiswa Penunggak: 15
CSV Rows: 800
Rejected Rows: 16
Valid Rows: 784
Dropout Rate: 2%
Data Quality Score: 100%
Gold Validation: PASS
UAT dummy: terkirim
```

## 9. Command Pipeline Manual

```powershell
python src\generators\generate_all.py
python src\validation\quality_gate.py
python src\transformations\bronze_ingest.py
python src\transformations\silver_clean.py
python src\transformations\gold_star_schema.py
python src\metrics\reconcile_control_total.py
python src\metrics\pipeline_latency.py
python src\metrics\data_freshness.py
python src\metrics\dropout_rate.py
python src\metrics\data_quality_score.py
python src\metrics\generate_uat.py
```

## 10. Command Test

```powershell
python -m pytest tests\ -v
```

Expected:

```text
8 passed
```

## 11. Command Trino Kontrol

```powershell
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(f.nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
```

Expected:

```text
"31250000","15"
```

## 12. Troubleshooting Dasar

Jika service belum ready:

```powershell
docker compose ps
docker compose logs --tail=100
```

Jika init container terlihat exited:

```powershell
docker inspect keuangan-airflow-init --format "{{.State.Status}} {{.State.ExitCode}}"
docker inspect keuangan-minio-init --format "{{.State.Status}} {{.State.ExitCode}}"
```

`Exited (0)` untuk init container adalah OK.

Jika portal belum terbuka:

```powershell
.\scripts\start_portal.ps1
```

Jika backend belum terbuka:

```powershell
.\scripts\start_portal_backend.ps1
```

Jika Superset belum sehat:

```powershell
Invoke-WebRequest -Uri "http://localhost:8089/health" -UseBasicParsing
docker compose logs --tail=100 superset
```

Jika Trino belum sehat:

```powershell
Invoke-WebRequest -Uri "http://localhost:8082/v1/info" -UseBasicParsing
docker compose logs --tail=100 trino
```

Jika angka metrics tidak sesuai expected:

```powershell
python src\generators\generate_all.py
python src\validation\quality_gate.py
python src\transformations\bronze_ingest.py
python src\transformations\silver_clean.py
python src\transformations\gold_star_schema.py
python src\metrics\reconcile_control_total.py
```

## 13. Catatan Data

Semua data untuk uji coba harus dummy. Jangan upload data pribadi riil.

Contoh data dummy yang valid:

```text
Mahasiswa Dummy 001
Mahasiswa Dummy 002
Mahasiswa Dummy 003
```

## Acceptance

- Cara menjalankan Docker dicantumkan: PASS.
- Cara cek container dicantumkan: PASS.
- Cara menjalankan portal/backend dicantumkan: PASS.
- Cara cek port dicantumkan: PASS.
- URL pengguna dicantumkan: PASS.
- Urutan trial dicantumkan: PASS.
- Expected result dicantumkan: PASS.
