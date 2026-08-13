# SILARAS SD Excel Lakehouse Architecture

SILARAS SD memakai workflow Excel untuk RAB, IKU, dan Nomenklatur. Gold adalah
model data terdenormalisasi berbasis laporan tahunan dengan struktur dimensional
secara logis; tidak ada tabel dimensi fisik yang wajib dibuat.

## Kontrak Gold tahunan

`gold.fact_anggaran` adalah satu-satunya tabel Gold utama dengan grain satu item
anggaran x satu alokasi IKU. `tahun` adalah satu-satunya atribut waktu analitik.
Informasi cakupan sumber disimpan pada Bronze/Silver dan lineage untuk audit,
bukan sebagai kolom analitik Gold.

Kunci pipeline adalah `dataset_session_id` dan `run_id`. Manifest tetap boleh
memakai `pipeline_run_id` sebagai identitas audit, tetapi nama tersebut tidak
digandakan menjadi kolom Gold.

Total Anggaran dihitung sebagai `SUM(jumlah_weighted_iku)`. Untuk setiap
kombinasi dataset, run, dan item, jumlah `allocation_weight` harus sama dengan
satu. Status rekonsiliasi adalah status validasi dari view, bukan metrik aditif.

## Data Flow

1. Portal backend menerima workbook melalui `/api/upload/excel-dataset`.
2. File sumber disimpan di `data/raw/excel_lakehouse/` beserta metadata lineage.
3. Pipeline `src/transformations/excel_lakehouse_pipeline.py` membentuk Bronze
   cell-level, Silver normalization, dan Gold `fact_anggaran`.
4. Sumber parsial pada tahun yang sama digabung bila identitas sumber tidak
   tumpang tindih. Sumber tahunan yang bertemu sumber parsial harus memiliki
   bukti cakupan; tanpa bukti pipeline berhenti dengan
   `AMBIGUOUS_SOURCE_OVERLAP`.
5. `src/storage/excel_storage_manifest.py` memetakan artefak ke raw, Bronze,
   Silver, Gold, reports, dan logs.
6. `src/sql/load_gold_to_postgres.py` memuat kontrak yang sama ke schema `gold`.
7. `src/sql/setup_superset_excel_assets.py` membuat dataset, filter, dan 13
   chart dari registry yang sama.
8. Portal lokal memprioritaskan Superset API dan memakai Gold lokal sebagai
   fallback yang terverifikasi.

## Active Gold Tables

- `gold.fact_anggaran`
- `gold.vw_dashboard_iku_anggaran`
- `gold.vw_dashboard_mapping_quality`
- `gold.vw_dashboard_reconciliation`
- `gold.vw_dashboard_detail_item`

## Dashboard contract

Filter: `tahun`, `prodi`, `iku`, `kegiatan`, `akun`.  
KPI: Total Anggaran, Jumlah Item, Jumlah IKU, Jumlah Kegiatan, dan Status Rekonsiliasi.

## Default Commands

```powershell
python src/transformations/excel_lakehouse_pipeline.py
python src/metrics/validate_excel_lakehouse_counts.py
python src/storage/excel_storage_manifest.py
python src/sql/load_gold_to_postgres.py
python src/status/system_truth_status.py
```
