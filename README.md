# Data Lakehouse Keuangan Prodi

Implementasi lokal Data Lakehouse berbasis Medallion Architecture untuk data keuangan perguruan tinggi. Proyek ini mengikuti rencana kerja di `end_to_end_plan_data_lakehouse_mcp_skills.md` dan dikerjakan secara checkpoint-based.

## Target

- Generate data dummy PDF, CSV, dan Excel.
- Validasi quality gate dan quarantine data rusak.
- Bangun Bronze, Silver, dan Gold layer.
- Bentuk star schema untuk analisis piutang UKT Prodi Sains Data.
- Hubungkan Gold layer Iceberg di MinIO ke Trino dan Superset.
- Hitung metrik evaluasi dan siapkan UAT dashboard.

## Nilai Kontrol

| Kontrol | Target |
|---|---:|
| Total tunggakan UKT Prodi Sains Data | 31250000 |
| Jumlah mahasiswa penunggak Sains Data | 15 |
| Total pagu RAB Sains Data | 150000000 |

## Quick Start

```powershell
Copy-Item .env.example .env
.\scripts\full_run.ps1
```

```powershell
make up
make full-run
```

Jika `make` tidak tersedia di Windows, gunakan:

```powershell
.\scripts\full_run.ps1
```

## Service URL

- Portal lokal semua service dan password: http://localhost:8090
- Portal backend API: http://localhost:8091/api/health
- Dashboard Superset Piutang UKT: http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/
- MinIO API health: http://localhost:9000/minio/health/live
- MinIO Console: http://localhost:9001
- Spark Master UI: http://localhost:8080
- Spark Worker UI: http://localhost:8081
- Spark Master RPC: localhost:7077
- Airflow: http://localhost:8085
- Trino info: http://localhost:8082/v1/info
- Superset health: http://localhost:8089/health
- PostgreSQL metastore: localhost:5432

Cek semua port lokal:

```powershell
.\scripts\check_ports.ps1
```

Jalankan portal lokal:

```powershell
.\scripts\start_portal.ps1
```

Default login:

- Airflow: `airflow` / `airflow`
- Superset: `admin` / `admin`

## Validasi Trino Iceberg

Gold mart utama dimuat sebagai tabel Iceberg di MinIO dengan metadata JDBC di PostgreSQL metastore, lalu di-query oleh Trino melalui catalog `iceberg`. Loader PostgreSQL lokal tetap tersedia sebagai fallback kompatibilitas.

```powershell
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(nominal_piutang_rp), COUNT(*) FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
```

Expected output:

```text
"31250000","15"
```

## Superset Dataset

Final run membuat database connection dan dataset Superset via API:

- Database: `Trino Iceberg Gold Keuangan`
- Dataset: `vw_dashboard_piutang_ukt`
- Dashboard: `Dashboard Piutang UKT Prodi`

Asset ID tersimpan di `outputs/reports/superset_assets.json` dan `outputs/reports/superset_dashboard.json`.

## Checkpoint

Progress tersimpan di `docs/checkpoints/`. Mulai dari `CHECKPOINT-00-setup.md` dan lanjut berurutan sampai `CHECKPOINT-09-final-run.md`.
