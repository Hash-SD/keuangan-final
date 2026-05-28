# CHECKPOINT-BE-MAIN-06: Activity Lineage API

## Tujuan
Menyelaraskan activity log dengan lineage dan task DAG pada `main.pdf`.

## File Dibaca
- portal_backend/services/activity.py
- portal_backend/services/pipeline.py
- outputs/reports/activity_log.json

## Dokumentasi Context7 yang Dibaca
- Python/cpython: json dan datetime.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- portal_backend/services/pipeline.py

## Implementasi
Activity action pipeline diselaraskan:
- `quality_gate_process`
- `extract_bronze`
- `clean_silver`
- `load_gold_schema`
- `validate_mart`
- `metrics`

Endpoint:
```text
GET /api/activity
```

## Command yang Dijalankan
```bash
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/pipeline/full-run-basic
Invoke-RestMethod -Uri http://localhost:8091/api/activity
```

## Hasil Validasi
Full-run basic menulis activity untuk setiap step dan endpoint activity tetap aman jika file belum ada.

## Masalah / Risiko
Activity log belum memakai rotasi lanjutan; dibatasi oleh helper backend pada 100 aktivitas terakhir.

## Keputusan Teknis
Timestamp tetap memakai zona Asia/Jakarta.

## Langkah Berikutnya
Integrasi frontend.

## Status
Selesai
