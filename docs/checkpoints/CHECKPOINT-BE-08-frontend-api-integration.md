# CHECKPOINT-BE-08: Frontend API Integration

## Tujuan
Menghubungkan UI Portal Keuangan dengan backend Flask.

## File Dibaca
- portal/index.html
- portal/server.py
- docs/checkpoints/CHECKPOINT-UI-*.md

## Dokumentasi Context7 yang Dibaca
- JavaScript Fetch API melalui dokumentasi Python/Flask dan pola JSON endpoint.
- Flask-CORS untuk akses frontend port 8090 ke backend port 8091.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal/index.html

## Implementasi
Frontend kini memanggil:
- `GET /api/metrics`
- `GET /api/status/services`
- `GET /api/activity`
- `GET /api/lakehouse/summary`
- `GET /api/data/preview`
- `GET /api/data/rejected-rows`
- `POST /api/upload/pdf`
- `POST /api/upload/csv`
- `POST /api/upload/excel`
- `POST /api/pipeline/<name>`
- `POST /api/uat/submit`

Jika backend tidak aktif, UI fallback ke `/api/portal-state` dari server statis lama dan tetap menampilkan empty state.

## Command yang Dijalankan
```bash
.\scripts\start_portal_backend.ps1
```

## Hasil Validasi
Frontend dapat menampilkan data backend, tombol upload memiliki loading/success/error state, tombol pipeline menjalankan endpoint backend, dan tidak ada error JavaScript pada pemeriksaan browser.

## Masalah / Risiko
Jika service Docker offline, kartu System menampilkan `offline`, sesuai fallback yang diharapkan.

## Keputusan Teknis
`API_BASE_URL` diarahkan ke `http://localhost:8091` agar backend dan frontend tetap terpisah jelas.

## Langkah Berikutnya
Membuat start script backend/frontend.

## Status
Selesai
