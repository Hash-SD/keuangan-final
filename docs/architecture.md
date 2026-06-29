# SILARAS SD Excel Lakehouse Architecture

SILARAS SD memakai workflow Excel-only untuk RAB, RPD/IKU, dan Nomenklatur.

## Data Flow

1. Portal backend menerima workbook Excel melalui `/api/upload/excel-dataset`.
2. File disimpan di `data/raw/excel_lakehouse/`.
3. Pipeline `src/transformations/excel_lakehouse_pipeline.py` membentuk Bronze cell-level, Silver normalization, dan Gold `fact_anggaran`.
4. `src/storage/excel_storage_manifest.py` memetakan artefak ke layer raw, bronze, silver, gold, reports, dan logs.
5. `src/sql/load_gold_to_postgres.py` memuat Gold ke schema `gold`.
6. `src/sql/setup_superset_excel_assets.py` membuat dataset dan dashboard dari `fact_anggaran`.

## Active Gold Tables

- `gold.fact_anggaran`
- `gold.vw_dashboard_iku_anggaran`
- `gold.vw_dashboard_mapping_quality`
- `gold.vw_dashboard_reconciliation`
- `gold.vw_dashboard_detail_item`

## Default Commands

```powershell
python src/transformations/excel_lakehouse_pipeline.py
python src/validation/excel_count_validation.py
python src/storage/excel_storage_manifest.py
python src/sql/load_gold_to_postgres.py
python src/status/system_truth_status.py
```
