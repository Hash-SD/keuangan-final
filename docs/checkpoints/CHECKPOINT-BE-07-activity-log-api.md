# CHECKPOINT-BE-07: Activity Log API

## Tujuan
Menyediakan activity log untuk upload dan eksekusi pipeline.

## File Dibaca
- outputs/reports/activity_log.json

## Dokumentasi Context7 yang Dibaca
- Python/cpython: `json`, `pathlib`, dan timestamp lokal.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal_backend/services/activity.py
- portal_backend/app.py
- portal_backend/services/files.py
- portal_backend/services/pipeline.py

## Implementasi
Endpoint dibuat:
```text
GET /api/activity
```

Backend menulis activity saat:
- upload dummy berhasil/gagal,
- pipeline command berhasil/gagal,
- full-run selesai.

## Command yang Dijalankan
```bash
Invoke-RestMethod -Uri http://localhost:8091/api/activity
```

## Hasil Validasi
Activity log dapat dibaca. Jika file belum ada, response tetap rapi dengan daftar kosong dan pesan belum ada aktivitas.

## Masalah / Risiko
Activity log lokal belum memakai rotasi file; untuk portal lokal ini masih cukup.

## Keputusan Teknis
Timestamp ditulis dalam zona `Asia/Jakarta`.

## Langkah Berikutnya
Menghubungkan frontend ke API backend.

## Status
Selesai
