# CHECKPOINT-BE-MAIN-09: End-to-End Validation

## Tujuan
Memvalidasi backend dan UI berdasarkan `main.pdf`.

## File Dibaca
- portal/index.html
- portal_backend/
- src/generators/
- src/validation/quality_gate.py
- src/transformations/
- src/metrics/
- tests/

## Dokumentasi Context7 yang Dibaca
- Flask: endpoint, JSON response, upload.
- Python/cpython: subprocess, pathlib, json, csv.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- docs/checkpoints/CHECKPOINT-BE-MAIN-00-context-alignment.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-01-backend-scaffold.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-02-pdf-csv-excel-status.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-03-quality-gate-api.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-04-medallion-api.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-05-metrics-api.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-06-activity-lineage-api.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-07-frontend-integration.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-08-uat-api.md
- docs/checkpoints/CHECKPOINT-BE-MAIN-09-e2e-validation.md

## Implementasi
Validasi mencakup:
- backend health berbasis `main.pdf`,
- PDF sample status,
- CSV/Excel source status,
- service status,
- metrics,
- lakehouse summary,
- activity,
- full-run-basic,
- pytest.

## Command yang Dijalankan
```bash
python src/generators/generate_all.py
python src/validation/quality_gate.py
python src/transformations/bronze_ingest.py
python src/transformations/silver_clean.py
python src/transformations/gold_star_schema.py
python src/metrics/reconcile_control_total.py
python src/metrics/pipeline_latency.py
python src/metrics/data_freshness.py
python src/metrics/dropout_rate.py
python src/metrics/data_quality_score.py
.\scripts\start_portal_backend.ps1
Invoke-RestMethod -Uri http://localhost:8091/api/health
Invoke-RestMethod -Uri http://localhost:8091/api/pdf/sample-status
Invoke-RestMethod -Uri http://localhost:8091/api/data/source-status
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/pipeline/full-run-basic
python -m pytest tests -v
```

## Hasil Validasi
- Backend berjalan.
- `/api/health` ok dengan `mode=local-on-premise` dan `basis=main.pdf`.
- `/api/pdf/sample-status` ok.
- `/api/data/source-status` ok: 2 CSV, 800 rows, Excel RAB ready.
- `/api/status/services` ok dan tidak crash saat Docker service offline.
- `/api/metrics` ok: Data Quality Score 100.0, Dropout Rate 2.0, reconcile pass.
- `/api/lakehouse/summary` ok.
- `/api/activity` ok.
- `/api/pipeline/full-run-basic` success.
- `python -m pytest tests -v`: 6 passed.

## Masalah / Risiko
Docker services Airflow/Superset/MinIO/Spark/Trino/PostgreSQL dapat offline jika stack belum dijalankan; endpoint status menampilkan offline sesuai rancangan lokal.

## Keputusan Teknis
Validasi akhir menggunakan mode local-basic agar tidak memaksa Iceberg/Trino/Superset automation.

## Langkah Berikutnya
Opsional: jalankan validasi full-docker setelah seluruh service Docker aktif.

## Status
Selesai
