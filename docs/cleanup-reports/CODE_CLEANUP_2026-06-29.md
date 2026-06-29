# Code Cleanup Report - 2026-06-29

## Summary
- UI utama portal sudah dipindahkan ke konsep Excel Lakehouse only.
- Artefak lokal aman yang dihapus: `test-results/` dan `main.pdf`.
- Panel upload legacy dan handler frontend lama sudah dihapus dari `portal/index.html`.
- File lama yang masih import-coupled belum dihapus agar tidak mematahkan compile/test secara diam-diam.

## Removed
- `test-results/`
  - Alasan: artefak hasil Playwright lama dan bukan bagian source sistem.
- `main.pdf`
  - Alasan: artefak PDF lama di root repo dan tidak relevan dengan portal Excel Lakehouse.

## Frontend Legacy Removed
- Menghapus panel upload-session lama dari UI.
- Menghapus handler frontend lama untuk staged upload per-file.
- Menghapus request frontend ke `/api/pdf/sample-status`.
- Menghapus istilah `PDF`, `CSV`, `Legacy`, dan `piutang` dari teks yang tampil di `portal/index.html`.
- Mengganti kartu lokasi data menjadi tombol copy path agar pengguna tidak perlu membaca detail teknis panjang.

## Still Present And Requires Refactor Before Deletion
File berikut masih ada karena masih direferensikan oleh modul lama, test lama, atau checkpoint lama:

- `src/generators/generate_pdf_audited.py`
- `src/generators/generate_csv_transactions.py`
- `src/extraction/extract_pdf_piutang.py`
- `src/validation/quality_gate.py`
- `src/transformations/bronze_ingest.py`
- `src/transformations/silver_clean.py`
- `src/transformations/gold_star_schema.py`
- `src/metrics/data_quality_score.py`
- `src/metrics/reconcile_control_total.py`
- `src/metrics/pipeline_latency.py`
- `portal_backend/services/upload_session.py`
- `portal_backend/services/reference.py`
- `portal_backend/services/pipeline.py`
- legacy checkpoint docs under `docs/checkpoints/`
- old tests under `tests/test_upload_session*.py`, `tests/test_quality_gate*.py`, and old Playwright upload tests.

## Data Candidates For Removal Or Archive
- `data/raw_lama/`
- `data/dummy_upload_skenario_multi_tahun/`
- `data/samples/ITERA_LKTA2024Audited.pdf`

These are data artifacts, so they should be removed only after confirming no test or demo workflow still reads them.

## Validation
- `portal/index.html` text scan: no visible legacy terms found for `PDF`, `CSV`, `Legacy`, `piutang`.
- Browser verification evidence:
  - `outputs/evidence/portal_uiux_refinement_check.json`
  - `outputs/evidence/portal_screenshots/ui_data_refined_desktop.png`
  - `outputs/evidence/portal_screenshots/ui_data_refined_mobile.png`
  - `outputs/evidence/portal_screenshots/ui_system_refined_desktop.png`
  - `outputs/evidence/portal_screenshots/ui_system_refined_mobile.png`

## Recommendation
Next cleanup should remove the old piutang pipeline as a separate refactor:
1. Move or delete old DAG `keuangan_prodi_lakehouse_dag.py`.
2. Remove old upload-session backend endpoints or turn them into explicit legacy-only endpoints.
3. Replace old tests with Excel-only upload/API tests.
4. Remove old generated PDF/CSV/data samples.
5. Run `python -m compileall src dags portal_backend` and targeted pytest after dependency cleanup.
