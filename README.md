# SILARAS SD

**Sistem Lakehouse Anggaran RAB dan IKU Sains Data**

SILARAS SD adalah sistem lakehouse anggaran berbasis Excel untuk **RAB, RPD/IKU, dan Nomenklatur** dengan arsitektur Medallion (Bronze → Silver → Gold). Pipeline utama berjalan *Excel-only*: cukup unggah workbook Excel, sistem memproses hingga dashboard BI.

## Arsitektur

```text
Raw Excel (RAB, RPD/IKU, Nomenklatur)
  -> Bronze   cell-level extraction
  -> Silver   flexible normalization & mapping IKU/nomenklatur
  -> Gold     fact_anggaran + view dashboard
  -> PostgreSQL / Iceberg / Trino
  -> Superset Dashboard IKU
  -> Portal SILARAS SD (v2) & superset-dashboard mirror
```

Stack platform:

- Docker Compose (12 service: postgres-metastore, minio, spark-master/worker, airflow, trino, superset, portal-backend, portal-frontend)
- Apache Airflow — orkestrasi pipeline
- Apache Spark — pemrosesan data
- MinIO / S3 — storage layer
- PostgreSQL — metastore + gold tables
- Apache Iceberg — tabel Gold di MinIO
- Trino — query engine (catalog postgres)
- Apache Superset — dashboard BI
- Portal frontend (React/TS-like + ECharts) & backend API (Flask)

## Struktur Repository

```text
dags/                          DAG Airflow utama
src/
  transformations/             pipeline Excel lakehouse (Bronze→Silver→Gold)
  sql/                         load ke PostgreSQL, setup aset Superset
  storage/                     storage manifest (MinIO/S3)
  status/                      system truth status
  metrics/                     validasi count, latency, freshness, UAT
  validation/                  quality gate, cross-engine check
portal/                        frontend: v2 (primer), local-dashboard, legacy
portal_backend/                Flask API (app.py + services/)
superset-dashboard/            dashboard mirror dari Superset API (Docker/Vercel)
tests/                         pytest (unit/integration) + Playwright (E2E)
```

## Output Utama

Bronze:

- `data/generated/bronze/bronze_excel_cells.parquet`

Silver:

- `data/generated/silver/silver_rab_items_flexible.parquet`
- `data/generated/silver/silver_rab_rows_classified.parquet`
- `data/generated/silver/silver_rab_formula_coverage.parquet`
- `data/generated/silver/silver_rab_orphan_items.parquet`
- `data/generated/silver/silver_detail_support_items.parquet`
- `data/generated/silver/silver_nomenklatur_detail.parquet`
- `data/generated/silver/silver_mapping.parquet`
- `data/generated/silver/silver_validation.parquet`

Gold:

- `data/generated/gold/fact_anggaran.parquet`
- `data/generated/gold/vw_dashboard_iku_anggaran.parquet`
- `data/generated/gold/vw_dashboard_mapping_quality.parquet`
- `data/generated/gold/vw_dashboard_reconciliation.parquet`
- `data/generated/gold/vw_dashboard_detail_item.parquet`

Reports:

- `outputs/reports/pipeline_run_summary.json`
- `outputs/reports/pipeline_count_validation.json`
- `outputs/reports/rab_reconciliation_report.json`
- `outputs/reports/storage_manifest.json`
- `outputs/reports/system_truth_status.json`
- `outputs/reports/service_health_report.json`

## fact_anggaran

Gold utama adalah `fact_anggaran` dengan grain:

```text
1 row = 1 item anggaran x 1 IKU allocation
```

Kolom utama:

```text
item_id
run_id
tahun
periode
prodi
fakultas
kegiatan
cluster_kegiatan
akun
kode_akun
nama_akun
iku
kode_iku
nama_iku
nomenklatur_path
uraian_detail
qty
satuan
harga_satuan
jumlah
allocation_weight
jumlah_weighted_iku
mapping_status
data_quality_flag
source_file
source_sheet
source_row
created_at
```

Aturan IKU:

- Satu item dengan satu IKU: `allocation_weight = 1`
- Satu item dengan banyak IKU: `allocation_weight = 1 / jumlah_iku`
- `jumlah_weighted_iku = jumlah * allocation_weight`

## Rekonsiliasi RAB Excel

Parser RAB menggunakan aturan strict reconciliation agar total Gold tidak membengkak:

- Sheet `RAB` adalah sumber utama nominal untuk `fact_anggaran`.
- Sheet rincian akun (`belanja bahan`, `perjalanan dinas`, `jasa profesi`, `belanja sewa`, dll.) disimpan sebagai `detail_support`, tetapi tidak dijumlahkan ke Gold jika sheet `RAB` tersedia.
- Baris subtotal, header, total, dan baris formula parent tidak masuk `fact_anggaran`.
- Leaf item yang tidak masuk formula parent terdekat diberi flag `orphan_not_in_parent_sum` dan dikeluarkan dari Gold secara default.
- Formula error (`#REF!`, `#VALUE!`, `#N/A`, `#DIV/0!`) masuk laporan rekonsiliasi.
- Warna/fill, bold, border, merged cell, dan formula disimpan sebagai metadata audit Bronze/Silver, bukan sebagai satu-satunya rule nominal.

Contoh RAB 2025:

- Gold total: `Rp235.746.266`
- Excluded orphan: `RAB!P16` sebesar `Rp300.000`
- Sheet rincian akun: disimpan sebagai supporting detail untuk mencegah double count

## Menjalankan Sample Pipeline

```powershell
$env:FINANCE_EXCEL_FILES='D:\Downloads\RAB 2025 SD RAB IKU.xlsx;D:\Downloads\Nomenklatur.xlsx;D:\Downloads\Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx;D:\Downloads\RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx;D:\Downloads\RAB_SD_Usulan KE (1)_jul-des 2023.xlsx'
python src\transformations\excel_lakehouse_pipeline.py
Copy-Item data\generated\excel_lakehouse_metadata.json outputs\reports\pipeline_run_summary.json -Force
python src\metrics\validate_excel_lakehouse_counts.py
python src\storage\excel_storage_manifest.py
python src\status\system_truth_status.py
```

Hasil sample terakhir:

- Bronze cells: `55340`
- Silver RAB items: `393`
- Nomenklatur detail: `248`
- fact_anggaran rows: `607`
- fact_anggaran weighted total: `Rp517.361.656`
- fact_anggaran weighted 2025: `Rp235.746.266`
- Count validation: `validated`

## Airflow

DAG utama:

```text
dags/keuangan_prodi_excel_lakehouse_dag.py
```

Flow:

```text
start
  -> validate_upload_context
  -> extract_excel_to_bronze
  -> detect_year_and_format
  -> parse_flexible
  -> merge_multi_file
  -> normalize_silver
  -> map_iku_and_nomenklatur
  -> validate_excel_totals
  -> build_fact_anggaran
  -> write_minio_storage        (storage manifest)
  -> load_gold_to_postgres
  -> validate_trino_postgres_catalog
  -> refresh_superset_dataset
  -> refresh_superset_dashboard
  -> generate_storage_manifest
  -> generate_system_status
  -> end
```

DAG menerima `dag_run.conf` untuk mengarahkan target Superset:

```text
dataset_session_id     session dataset yang diproses
pipeline_run_id        id run pipeline
dashboard_mode         update | create
dashboard_database_id  id database Superset target (opsional)
dashboard_dashboard_id id dashboard Superset target (opsional)
```

## Portal v2 (Primer)

Portal berjalan di `http://localhost:8088` (frontend) dan disajikan backend di `/v2`.

Area utama:

- **Orkestrasi** — trigger pipeline, pilih dataset aktif, monitor status DAG & progress task
- **Verifikasi IKU** — review dan override mapping IKU sebelum build Gold
- **Riwayat Data** — dataset, lineagem dan pipeline runs
- **Dashboard BI** — ringkasan anggaran, KPI, quality, dan pipeline status
- **Evaluasi UAT** — matriks UAT resmi + riwayat evaluasi pengguna
- **Status Server** — health service, system truth, dan service table

Alur unggah (Excel-only):

1. `POST /api/upload/excel-dataset` — unggah workbook + pilih tahun, mode dashboard, target database/dashboard Superset (opsional)
2. Dataset terekam di registry & disimpan sebagai `active` dataset
3. Trigger pipeline via Airflow; progress task muncul real-time di portal
4. Data tersaji di dashboard lokal & Superset

## Portal Backend — API

### Umum & status

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/health` | Health check |
| GET | `/api/readiness` | Readiness probe |
| GET | `/api/production/readiness` | Production readiness gate |
| GET | `/api/runtime-config` | Konfigurasi runtime |
| GET | `/api/runtime-context` | Konteks runtime |
| GET | `/api/metrics` | Metrik pipeline |
| GET | `/api/status/services` | Status service |
| GET | `/api/system-truth/status` | System truth status |
| GET | `/api/activity` | Log aktivitas |
| GET | `/api/activity/recent` | Aktivitas terbaru |
| POST | `/api/system/shutdown` | Shutdown container (`501` — belum diimplementasikan di backend lokal) |

### Upload & dataset

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/upload/excel-lakehouse` | Unggah workbook pipeline |
| POST | `/api/upload/excel-dataset` | Commit dataset Excel aktif |
| GET | `/api/upload/session/status` | Status sesi unggah |
| GET | `/api/datasets` | Daftar dataset |
| GET | `/api/excel-lakehouse/status` | Status lakehouse |

### Pipeline & Airflow

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/airflow/trigger` | Trigger DAG |
| GET | `/api/airflow/active` | DAG run aktif |
| GET | `/api/airflow/latest` | Run terakhir |
| GET | `/api/airflow/runs` | Daftar run |
| GET | `/api/airflow/runs/<run_id>` | Detail run + progress task |
| POST | `/api/pipeline/<name>` | Jalankan pipeline bernama |
| POST | `/api/pipeline/run/<run_id>` | Jalankan ulang run |
| GET | `/api/pipeline/status/<run_id>` | Status run |

### Data & kualitas

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/data/source-status` | Status file sumber |
| GET | `/api/data/preview` / `/api/preview/<layer>` | Preview data |
| GET | `/api/data/rejected-rows` | Baris ditolak |
| GET | `/api/data-quality/<run_id>` | Kualitas data run |
| GET | `/api/lakehouse/summary` | Ringkasan lakehouse |

### Review IKU & mapping

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/iku-review/queue` | Antrean review IKU |
| POST | `/api/iku-review/override` | Simpan override IKU |
| GET | `/api/mapping-review/queue` | Antrean review mapping |

### Storage & laporan

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/storage/manifest` | Manifest terakhir |
| GET | `/api/storage/manifest/<run_id>` | Manifest per run |
| GET | `/api/reports/bab4-evidence` | Laporan evidence |

### Dashboard lokal & Superset

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/local-dashboard/all` | Data lengkap dashboard lokal |
| GET | `/api/local-dashboard/status` | Status data |
| GET | `/api/local-dashboard/filters` | Opsi filter |
| GET | `/api/local-dashboard/summary` | Ringkasan |
| GET | `/api/local-dashboard/charts` | Data chart |
| GET | `/api/local-dashboard/table` | Data tabel |
| GET | `/api/dashboard/links/<run_id>` | Link dashboard per run |
| GET | `/api/superset/assets` | Aset Superset |
| GET | `/api/superset/status` | Status Superset |
| GET | `/api/superset/summary` | Ringkasan Superset |
| GET | `/api/superset/databases` | Daftar database Superset |
| GET | `/api/superset/dashboards` | Daftar dashboard Superset |
| GET | `/api/superset/chart-data` | Data chart dari Superset |

### UAT

| Metode | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/uat/summary` | Ringkasan matriks UAT |
| POST | `/api/uat/submit` | Submit evaluasi UAT |

Dashboard lokal mencoba membaca data dari Superset API terlebih dahulu (`/api/v1/chart/data`). Jika Superset tidak tersedia, dashboard fallback secara faktual ke Gold `fact_anggaran` lokal dan menandai `source_kind` sebagai `gold_fact_anggaran`.

## Superset

Script aset dashboard:

```text
src/sql/setup_superset_excel_assets.py
```

Dashboard minimal:

- Executive KPI
- Anggaran per IKU
- Cluster Kegiatan
- Detail Item Biaya
- Komposisi Akun
- Mapping Quality

Dataset: `gold.fact_anggaran`

Atribut teknis berikut **tidak ditampilkan** di Superset (dinonaktifkan di level dataset; kolom tetap ada di tabel `gold.fact_anggaran` untuk lineage/QA dan dapat diakses via SQL Lab):

- `mapping_status`
- `data_quality_flag`
- `source_sheet`
- `source_row`

Script juga membuat **Saved Queries** untuk pengecekan:

- `SILARAS - Detail Item Biaya (tanpa kolom teknis)` — data faktual tanpa atribut teknis
- `SILARAS - Cek Kolom Teknis (audit)` — verifikasi kolom teknis masih eksis di tabel

### Target database & dashboard

Pipeline dapat diarahkan ke target spesifik via env/`dag_run.conf`:

```text
SUPERSET_DATABASE_ID    id database Superset (jika diisi, harus eksis; selain itu cari/match nama)
SUPERSET_DASHBOARD_ID   id dashboard Superset (jika diisi, harus eksis; selain itu slug/upsert)
SUPERSET_DATABASE_NAME  fallback nama database (default: gold_...)
```

- Jika `SUPERSET_DATABASE_ID` diisi namun id tidak ditemukan → pipeline gagal (fail fast).
- Jika `SUPERSET_DASHBOARD_ID` diisi namun id tidak eksis → fallback ke slug/upsert.
- Portal v2 memvalidasi target saat upload: id non-digit ditolak.

## superset-dashboard (mirror)

Dashboard mirror di `superset-dashboard/` menarik data langsung dari REST API Superset (tidak membaca DB langsung). Menjalankan via Docker (menumpang network `lakehouse_net`) atau Vercel.

```bash
cd superset-dashboard
python server.py   # -> http://localhost:8092/
```

Detail: [superset-dashboard/README.md](superset-dashboard/README.md)

## Storage / MinIO

Manifest:

```text
outputs/reports/storage_manifest.json
```

Prefix wajib:

```text
s3://lakehouse/raw/
s3://lakehouse/bronze/
s3://lakehouse/silver/
s3://lakehouse/gold/
s3://lakehouse/reports/
s3://lakehouse/logs/
```

Status manifest:

- `uploaded` — minimal satu entry berhasil di-upload (bukan skipped) dan semua non-skipped berstatus uploaded
- `mapped_not_uploaded` — file terpetakan tapi belum di-upload ke MinIO (default)
- `not_ready` — run_id/session belum tersedia

Untuk upload ke MinIO:

```powershell
$env:MINIO_UPLOAD_ENABLED='true'
$env:MINIO_ENDPOINT='http://localhost:9000'
$env:MINIO_BUCKET='lakehouse'
python src\storage\excel_storage_manifest.py
```

## Docker

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose up -d
```

Layanan utama:

- Portal frontend + backend
- Airflow (webserver + scheduler)
- Spark (master + worker)
- MinIO + PostgreSQL + Trino + Superset

Makefile menyediakan shortcut: `make setup`, `make up`, `make down`, `make logs`, `make full-run`, `make test`, `make setup-superset`, `make truth-status`.

## Testing

```powershell
python -m compileall src dags portal_backend
python -m pytest tests/ -q
```

Cakupan test:

- **Pipeline Excel** — Bronze extraction, parse 2023/2024/2025, RAB amount columns, money normalization, multi-file merge, nomenklatur, IKU allocation, fact_anggaran build
- **Upload & produksi** — Excel-only upload API, production source guard, upload atomic, pipeline atomic, published-sources guard
- **Portal** — routes, security, static server, v2 contract, v2 runtime, backend interactions, readiness endpoints
- **Status & sistem** — system truth (staging), service health, minio unreachable, superset offline, completed/empty/etl-without-uat states, UAT matrix & truth
- **Dashboard** — local dashboard, superset API bridge, dashboard target selection, gold view filters
- **Airflow** — DAG imports & final tasks, trigger conf (dataset/pipeline identity, dashboard target), rejection reporting

E2E (Playwright):

```powershell
npx playwright test tests/playwright/local-dashboard.spec.ts
npx playwright test tests/playwright/superset-dashboard.spec.ts
```

Satu test sample workbook di-skip jika workbook sumber tidak tersedia di mesin lokal — hal tersebut diharapkan.

## Repository Scope

Kode, data, test, dan dokumentasi pada branch ini diarahkan ke workflow Excel Lakehouse RAB/IKU/Nomenklatur. Portal v2 adalah antarmuka primer; Superset dan mirror-nya adalah lapisan BI.
