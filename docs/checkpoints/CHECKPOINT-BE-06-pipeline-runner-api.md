# CHECKPOINT-BE-06: Pipeline Runner API

## Tujuan
Menjalankan command pipeline lokal dari API secara aman.

## File Dibaca
- Makefile
- src/generators/generate_all.py
- src/validation/quality_gate.py
- src/transformations/bronze_ingest.py
- src/transformations/silver_clean.py
- src/transformations/gold_star_schema.py
- src/metrics/reconcile_control_total.py
- src/metrics/pipeline_latency.py
- src/metrics/data_freshness.py
- src/metrics/dropout_rate.py
- src/metrics/data_quality_score.py
- src/metrics/generate_uat.py

## Dokumentasi Context7 yang Dibaca
- Python/cpython: `subprocess.run` dengan list argument, timeout, stdout/stderr capture, dan `check=False`.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal_backend/services/pipeline.py
- portal_backend/app.py
- src/generators/generate_pdf_audited.py

## Implementasi
Endpoint pipeline dibuat:
```text
POST /api/pipeline/generate-data
POST /api/pipeline/quality-gate
POST /api/pipeline/bronze
POST /api/pipeline/silver
POST /api/pipeline/gold
POST /api/pipeline/metrics
POST /api/pipeline/validate-gold
POST /api/pipeline/full-run
```

Semua command dijalankan dengan list argument dan tidak menggunakan `shell=True`.

## Command yang Dijalankan
```bash
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/pipeline/validate-gold
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/pipeline/full-run -Body '{"mode":"local-basic"}' -ContentType 'application/json'
```

## Hasil Validasi
`validate-gold` berhasil. `full-run` local-basic berhasil setelah generator PDF audited disesuaikan agar data dummy Prodi Sains Data konsisten dengan kontrol:
- Total piutang: `31250000`
- Jumlah penunggak: `15`
- Status reconcile: `pass`

## Masalah / Risiko
Mode `full-docker` belum dipaksa berjalan karena service Docker dapat offline. Mode aman yang divalidasi adalah `local-basic`.

## Keputusan Teknis
Generator dummy disesuaikan agar Sains Data selalu menghasilkan 15 baris kontrol dan tidak tercampur baris random tambahan.

## Langkah Berikutnya
Merapikan activity log API.

## Status
Selesai
