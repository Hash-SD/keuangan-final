# Cleanup Plan - Final SILARAS SD Branch

Branch: `feature/excel-lakehouse-v2-final`

## KEEP

- `docker-compose.yml`
- `config/airflow`, `config/spark`, `config/trino`, `config/superset`
- `portal/` sebagai shell UI
- `portal_backend/` sebagai backend platform
- `src/common/`, `src/storage/`, `src/sql/load_gold_to_postgres.py`
- `dags/keuangan_prodi_excel_lakehouse_dag.py`
- Modul baru `src/excel_ingestion`, `src/parser_flexible`, `src/mapping`, `src/gold`

## MODIFY

- `portal_backend/app.py`: tambahkan endpoint Excel-only dan pipeline SILARAS SD.
- `portal_backend/services/pipeline.py`: jadikan `excel-lakehouse` command pipeline baru.
- `portal_backend/services/lakehouse.py`: Gold summary membaca `fact_anggaran`.
- `src/status/system_truth_status.py`: layer status memprioritaskan Excel artifacts jika tersedia.
- `src/sql/load_gold_to_postgres.py`: load `fact_anggaran` dan view dashboard Excel.
- `src/transformations/load_gold_iceberg.py`: publish `fact_anggaran` dan dashboard views.
- `README.md`: fokus ke SILARAS SD.

## REPLACE

- Domain default pipeline lama PDF/CSV/piutang diganti pipeline Excel-only.
- Superset dashboard utama diarahkan ke `fact_anggaran`.
- Upload utama diarahkan ke Excel multi-file.

## LEGACY

- `src/extraction/extract_pdf_piutang.py`
- `src/generators/generate_pdf_audited.py`
- `src/transformations/gold_star_schema.py`
- `dags/keuangan_prodi_lakehouse_dag.py`
- Test lama piutang/PDF tetap dibiarkan sebagai legacy guard sampai fase penghapusan lebih agresif.

## REMOVE_FROM_FINAL_BRANCH

Tidak ada penghapusan fisik agresif pada pass ini. Alasannya:

- Banyak endpoint/test lama masih mengimpor modul PDF/piutang.
- Penghapusan langsung akan membuat `python -m pytest` gagal sebelum replacement portal penuh selesai.
- Sistem lama tetap aman di `main`; di branch final ini domain lama diturunkan menjadi legacy/non-default terlebih dahulu.

## DO_NOT_TOUCH

- `.git/`
- `.env`
- `data/raw/` dan file user
- `outputs/` secara keseluruhan
- Docker/service config yang masih dipakai stack

## Validation Required

- `python -m compileall src dags portal_backend`
- `python -m pytest`
- Sample pipeline Excel.
- Storage manifest Excel.
- Pipeline count validation.
