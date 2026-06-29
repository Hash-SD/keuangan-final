# Code Cleanup Report - 2026-06-29

## Summary

- Repository final difokuskan pada Excel Lakehouse RAB/IKU/Nomenklatur.
- Modul, endpoint, test, script, dan data dari konsep sebelumnya sudah dipangkas dari alur aktif.
- Validasi dokumentasi Context7 dipakai untuk pola Flask JSON API dan pytest discovery.

## Removed

- DAG lama non-Excel.
- Service backend upload bertahap lama dan service referensi lama.
- Generator, ekstraksi, transformasi, metrik, SQL, dan dashboard dari konsep sebelumnya.
- Test lama yang mengunci alur non-Excel.
- Playwright spec lama untuk workflow upload bertahap.
- Data sample, staging, raw, generated, dan quarantine dari workflow sebelumnya.
- Dokumen/checkpoint lama yang menjelaskan konsep sebelum Excel Lakehouse final.

## Kept

- Parser Excel 2023, 2024, 2025-like, dan Nomenklatur.
- Pipeline `excel_lakehouse_pipeline.py`.
- Storage manifest Excel.
- Superset Excel assets.
- Gold `fact_anggaran`.
- Portal frontend/backend Excel-only.
- Test yang memvalidasi Bronze/Silver/Gold Excel, upload API Excel, MinIO manifest, status sistem, dan dashboard Excel.

## Validation

- `python -m compileall src dags portal_backend`: PASS.
- Pytest dijalankan setelah cleanup dan hasil final dicatat di evidence/report terkait.
