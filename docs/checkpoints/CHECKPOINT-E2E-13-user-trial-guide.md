# CHECKPOINT-E2E-13 - User Trial Guide

Tanggal: 2026-05-28
Status: PASS

## 1. Jalankan Docker

```powershell
cd C:\Users\hm\keuangan-final
docker compose up -d
```

Validasi:

```powershell
docker compose ps
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_ports.ps1
```

## 2. Jalankan Portal Frontend

```powershell
.\scripts\start_portal.ps1
```

URL:

```text
http://localhost:8090
```

## 3. Jalankan Backend API

```powershell
.\scripts\start_portal_backend.ps1
```

Health check:

```text
http://localhost:8091/api/health
```

## 4. URL Service

```text
Portal:         http://localhost:8090
Backend health: http://localhost:8091/api/health
Airflow:        http://localhost:8085
Superset:       http://localhost:8089
Superset dash:  http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/
MinIO Console:  http://localhost:9001
MinIO API:      http://localhost:9000/minio/health/live
Spark Master:   http://localhost:8080
Spark Worker:   http://localhost:8081
Trino info:     http://localhost:8082/v1/info
```

Credential default:

```text
Airflow:  airflow / airflow
Superset: admin / admin
MinIO:    minioadmin / minioadmin
Postgres: lakehouse / lakehouse, database metastore
```

## 5. Urutan Uji Coba Pengguna

1. Buka `http://localhost:8090`.
2. Buka halaman `Beranda` dan cek KPI ringkas.
3. Buka halaman `System` dan pastikan service utama `Online`.
4. Buka halaman `Data` dan cek status PDF, CSV, Excel.
5. Buka halaman `Orkestrasi`.
6. Klik `Run Quality Gate`.
7. Klik `Run Bronze`.
8. Klik `Run Silver`.
9. Klik `Run Gold`.
10. Klik `Validate Gold`.
11. Klik `Full Run Basic`.
12. Buka halaman `Dashboard` dan cek metrics.
13. Buka halaman `Lakehouse` dan cek Bronze/Silver/Gold `Ready`.
14. Buka halaman `Analytics` dan klik `Submit UAT dummy`.
15. Buka Superset Dashboard.

## 6. Expected Result

```text
Total piutang UKT Sains Data: Rp31.250.000
Mahasiswa penunggak Sains Data: 15
Rejected rows quality gate: 16
Valid rows quality gate: 784
Total rows transaksi: 800
Dropout rate: 2%
Data quality score: 100%
Gold validation: PASS
UAT dummy: terkirim
Superset dashboard: tersedia
Trino query kontrol: "31250000","15"
```

## 7. Command Validasi Teknis

Generate data dan pipeline basic:

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

Load SQL dan BI:

```powershell
python src\sql\load_gold_to_postgres.py
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
python src\sql\setup_superset_assets.py
python src\sql\setup_superset_dashboard.py
```

Query Trino kontrol:

```powershell
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(f.nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
```

Expected:

```text
"31250000","15"
```

Test otomatis:

```powershell
python -m pytest tests\ -v
```

Expected:

```text
8 passed
```

## 8. Troubleshooting Dasar

Jika port check gagal:

```powershell
docker compose ps
docker compose logs --tail=100
```

Jika portal belum terbuka:

```powershell
.\scripts\start_portal.ps1
```

Jika backend belum terbuka:

```powershell
.\scripts\start_portal_backend.ps1
```

Jika Superset belum sehat, tunggu 30-60 detik lalu cek:

```powershell
Invoke-WebRequest -Uri "http://localhost:8089/health" -UseBasicParsing
docker compose logs --tail=100 superset
```

Jika Trino query gagal, cek service dan catalog:

```powershell
Invoke-WebRequest -Uri "http://localhost:8082/v1/info" -UseBasicParsing
docker compose logs --tail=100 trino
```

Jika angka metrics berubah tidak sesuai expected, ulangi full basic pipeline dan cek rekonsiliasi:

```powershell
python src\generators\generate_all.py
python src\validation\quality_gate.py
python src\transformations\bronze_ingest.py
python src\transformations\silver_clean.py
python src\transformations\gold_star_schema.py
python src\metrics\reconcile_control_total.py
```

## 9. Catatan Data

Semua data uji harus dummy. Pola sample yang tervalidasi menggunakan nama seperti:

```text
Mahasiswa Dummy 001
Mahasiswa Dummy 002
Mahasiswa Dummy 003
```

Jangan memasukkan data pribadi riil ketika mencoba fitur upload.

## Acceptance

- Pengguna bisa mengikuti panduan tanpa membaca kode: PASS.
- Semua URL dicantumkan: PASS.
- Credential dicantumkan: PASS.
- Urutan trial dicantumkan: PASS.
- Expected result dicantumkan: PASS.
- Troubleshooting dasar dicantumkan: PASS.
