# SILARAS SD

Sistem Lakehouse Anggaran RAB dan IKU Sains Data

SILARAS SD adalah Sistem Lakehouse Anggaran RAB dan IKU Sains Data berbasis Excel untuk RAB, RPD/IKU, dan Nomenklatur. Branch final ini berfokus pada workflow Excel-only dengan Medallion Architecture.

## Arsitektur

```text
Raw Excel
  -> Bronze cell-level
  -> Silver flexible normalization
  -> Gold fact_anggaran
  -> PostgreSQL / Iceberg / Trino
  -> Superset Dashboard IKU
  -> Portal SILARAS SD
```

Stack platform tetap dipertahankan:

- Docker Compose
- Apache Airflow
- Apache Spark
- MinIO / S3-compatible storage
- PostgreSQL metastore
- Apache Iceberg
- Trino
- Apache Superset
- Portal frontend
- Portal backend API

## Domain Baru

Sumber data utama:

- Excel RAB
- Excel RPD / IKU jika tersedia
- Excel Nomenklatur
- Multi-file per tahun

Sistem hanya membutuhkan workbook Excel untuk pipeline utama.

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
- Sheet rincian akun seperti `belanja bahan`, `perjalanan dinas`, `jasa profesi`, `belanja sewa`, dan sheet pendukung lain disimpan sebagai `detail_support`, tetapi tidak dijumlahkan ke Gold jika sheet `RAB` tersedia.
- Baris subtotal, header, total, dan baris formula parent tidak masuk `fact_anggaran`.
- Leaf item yang tidak masuk formula parent terdekat diberi flag `orphan_not_in_parent_sum` dan dikeluarkan dari Gold secara default.
- Formula error seperti `#REF!`, `#VALUE!`, `#N/A`, dan `#DIV/0!` masuk laporan rekonsiliasi.
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

DAG utama baru:

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
  -> write_minio_storage
  -> load_gold_to_postgres
  -> load_gold_to_iceberg
  -> refresh_superset_dataset
  -> refresh_superset_dashboard
  -> generate_storage_manifest
  -> generate_system_truth_status
  -> end
```

## Portal dan Backend

Endpoint Excel-only:

- `POST /api/upload/excel-dataset`
- `GET /api/datasets`
- `GET /api/pipeline/status/{run_id}`
- `POST /api/pipeline/run/{run_id}`
- `GET /api/storage/manifest/{run_id}`
- `GET /api/data-quality/{run_id}`
- `GET /api/dashboard/links/{run_id}`
- `GET /api/excel-lakehouse/status`

Endpoint pipeline:

- `POST /api/pipeline/excel-lakehouse`
- `POST /api/pipeline/excel-count-validation`
- `POST /api/pipeline/excel-storage-manifest`
- `POST /api/pipeline/load-gold-postgres`
- `POST /api/pipeline/superset-excel`

Endpoint dashboard lokal dan Superset:

- `GET /api/local-dashboard/all`
- `GET /api/local-dashboard/status`
- `GET /api/local-dashboard/filters`
- `GET /api/local-dashboard/summary`
- `GET /api/local-dashboard/charts`
- `GET /api/local-dashboard/table`
- `GET /api/superset/assets`
- `GET /api/superset/chart-data`

Dashboard lokal mencoba membaca data dari Superset API terlebih dahulu melalui
`/api/v1/chart/data`. Jika Superset tidak tersedia, dashboard fallback secara
faktual ke Gold `fact_anggaran` lokal dan menandai `source_kind` sebagai
`gold_fact_anggaran`.

## Superset

Script dashboard Excel:

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

Dataset:

```text
gold.fact_anggaran
```

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

Secara default manifest berjalan `mapped_not_uploaded`. Untuk upload ke MinIO:

```powershell
$env:MINIO_UPLOAD_ENABLED='true'
$env:MINIO_ENDPOINT='http://localhost:9000'
$env:MINIO_BUCKET='lakehouse'
python src\storage\excel_storage_manifest.py
```

## Docker

```powershell
docker compose up -d
```

Layanan utama:

- Portal frontend
- Portal backend
- Airflow
- Spark
- MinIO
- PostgreSQL
- Trino
- Superset

## Testing

```powershell
python -m compileall src dags portal_backend
python -m pytest
```

Test Excel utama:

- Bronze extraction
- 2023 multi-file parsing
- 2024 parser compatibility
- 2025-like parsing
- Nomenklatur parsing
- Multi-file merge
- IKU allocation
- fact_anggaran build
- Excel-only upload API
- Pipeline sample integration

## Repository Scope

Kode, data, test, dan dokumentasi pada branch ini diarahkan ke workflow Excel Lakehouse RAB/IKU/Nomenklatur.
