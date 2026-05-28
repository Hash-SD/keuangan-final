# CHECKPOINT-BE-09: Start Scripts

## Tujuan
Menyediakan satu script PowerShell untuk menjalankan backend dan frontend lokal.

## File Dibaca
- scripts/start_portal.ps1
- portal_backend/app.py

## Dokumentasi Context7 yang Dibaca
- Flask: menjalankan app lokal.
- Python/cpython: eksekusi modul Python.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- scripts/start_portal_backend.ps1

## Implementasi
Script baru:
```text
scripts/start_portal_backend.ps1
```

Fungsi:
- membuat `.env` dari `.env.example` jika belum ada,
- menjalankan backend di port 8091,
- menjalankan frontend di port 8090 jika belum aktif,
- mengecek `/api/health`,
- menampilkan URL portal dan backend.

## Command yang Dijalankan
```bash
.\scripts\start_portal_backend.ps1
```

## Hasil Validasi
Script berhasil menampilkan:
```text
Portal frontend aktif: http://localhost:8090
Portal backend aktif: http://localhost:8091/api/health
```

## Masalah / Risiko
Script tidak menghentikan proses lama otomatis jika port sudah digunakan; ia memakai proses yang sudah aktif.

## Keputusan Teknis
Frontend tetap menggunakan `scripts/start_portal.ps1` agar alur kerja lama tidak berubah.

## Langkah Berikutnya
Validasi end-to-end.

## Status
Selesai
