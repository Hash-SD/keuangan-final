# CHECKPOINT-DATA-07: Backend Reference API

## Tujuan
Menambahkan API referensi UKT/SPI.

## File Dibaca
- portal_backend/app.py
- portal_backend/services/reference.py
- portal_backend/services/paths.py

## Dokumentasi Context7 yang Dibaca
- Flask: JSON endpoint.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- portal_backend/app.py
- portal_backend/services/reference.py
- portal_backend/services/paths.py

## Implementasi
Endpoint baru:
```text
GET /api/reference/ukt
GET /api/reference/spi
GET /api/reference/summary
```

Preview dibatasi maksimal 25 rows oleh helper `csv_preview`.

## Command yang Dijalankan
```bash
Invoke-RestMethod -Uri http://localhost:8091/api/reference/summary
Invoke-RestMethod -Uri "http://localhost:8091/api/reference/ukt?limit=3"
Invoke-RestMethod -Uri "http://localhost:8091/api/reference/spi?limit=3"
```

## Hasil Validasi
Summary mengembalikan 41 prodi, 328 rows UKT, 41 rows SPI, dan status Excel/PDF.

## Masalah / Risiko
Tidak ada.

## Keputusan Teknis
API mengembalikan path relatif, bukan path absolut Windows.

## Langkah Berikutnya
Integrasi UI.

## Status
Selesai
