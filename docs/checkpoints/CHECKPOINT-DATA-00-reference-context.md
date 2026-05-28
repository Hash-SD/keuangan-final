# CHECKPOINT-DATA-00: Reference Context

## Tujuan
Mencatat konteks integrasi PDF sample dan master UKT/SPI ITERA.

## File Dibaca
- data/samples/ITERA_LKTA2024Audited.pdf
- main.pdf
- src/generators/
- portal_backend/services/reference.py

## Dokumentasi Context7 yang Dibaca
- Flask: JSON endpoint dan upload.
- Python/cpython: pathlib, csv, json, subprocess.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint backend sebelumnya.

## File Dibuat/Diubah
- Belum ada pada checkpoint ini.

## Implementasi
Konteks:
- PDF sample: `data/samples/ITERA_LKTA2024Audited.pdf`
- Master UKT: 41 prodi, 328 kombinasi prodi-golongan
- Master SPI: 41 prodi
- Semua data transaksi, mahasiswa, dan piutang bersifat dummy.

## Command yang Dijalankan
```bash
python -m pytest tests -v
```

## Hasil Validasi
Path PDF sample diperlakukan relatif dan endpoint backend tetap aman jika file tidak ada.

## Masalah / Risiko
PDF sample besar tetap tidak dimasukkan commit.

## Keputusan Teknis
Generator memakai struktur dummy UKT/SPI, bukan data pribadi riil.

## Langkah Berikutnya
Membuat generator master UKT/SPI.

## Status
Selesai
