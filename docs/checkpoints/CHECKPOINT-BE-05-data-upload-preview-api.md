# CHECKPOINT-BE-05: Data Upload Preview API

## Tujuan
Menyediakan upload dummy PDF/CSV/Excel, preview CSV, dan rejected rows.

## File Dibaca
- data/raw/pdf/
- data/raw/csv/
- data/raw/excel/
- data/quarantine/logs/rejected_rows.csv

## Dokumentasi Context7 yang Dibaca
- Flask: `request.files`, upload file, JSON response.
- Werkzeug: `secure_filename`.
- Python/cpython: `csv` reader dan path resolution.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal_backend/services/files.py
- portal_backend/app.py
- portal_backend/services/activity.py

## Implementasi
Endpoint dibuat:
```text
POST /api/upload/pdf
POST /api/upload/csv
POST /api/upload/excel
GET  /api/data/preview
GET  /api/data/rejected-rows
```

Validasi upload:
- Ekstensi dibatasi per jenis file.
- Nama file disanitasi.
- Path traversal dicegah dengan pengecekan root target.
- Ukuran request dibatasi 25 MB.

## Command yang Dijalankan
```bash
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/upload/csv -Form @{ file = Get-Item $env:TEMP\portal-upload-test\dummy_upload.csv }
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/upload/excel -Form @{ file = Get-Item $env:TEMP\portal-upload-test\dummy_upload.xlsx }
Invoke-RestMethod -Method Post -Uri http://localhost:8091/api/upload/pdf -Form @{ file = Get-Item $env:TEMP\portal-upload-test\dummy_upload.pdf }
Invoke-RestMethod -Uri "http://localhost:8091/api/data/preview?layer=gold&limit=3"
Invoke-RestMethod -Uri "http://localhost:8091/api/data/rejected-rows"
```

## Hasil Validasi
Upload dummy PDF/CSV/Excel berhasil. Preview CSV dibatasi, rejected rows mengembalikan empty state atau isi file jika tersedia.

## Masalah / Risiko
Upload hanya untuk data dummy lokal. File besar ditolak dengan JSON 413.

## Keputusan Teknis
Preview maksimal 25 baris agar frontend tidak memuat CSV besar.

## Langkah Berikutnya
Membuat endpoint pipeline runner.

## Status
Selesai
