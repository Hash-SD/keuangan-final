# CHECKPOINT-BE-MAIN-02: PDF CSV Excel Status

## Tujuan
Menyediakan API status sumber data berdasarkan `main.pdf`.

## File Dibaca
- data/samples/ITERA_LKTA2024Audited.pdf
- data/raw/pdf/ITERA_LKTA2024Audited.pdf
- data/raw/csv/transaksi_ganjil.csv
- data/raw/csv/transaksi_genap.csv
- data/raw/excel/rab_prodi_sains_data.xlsx

## Dokumentasi Context7 yang Dibaca
- Flask: JSON endpoint.
- Python/cpython: pathlib dan csv.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- portal_backend/services/reference.py
- portal_backend/services/paths.py
- portal_backend/app.py
- src/generators/generate_csv_transactions.py

## Implementasi
Endpoint dibuat:
```text
GET /api/pdf/sample-status
GET /api/data/source-status
```

CSV generator diperbarui dengan kolom dummy sesuai proposal:
`transaction_id`, `nim_dummy`, `tanggal`, `semester`, `tahun_akademik`, `jenis_biaya`, `prodi`, `fakultas`, `golongan_ukt`, `nominal_tagihan`, `nominal_bayar`, `status_bayar`, `metode_bayar`, `batch_id`.

## Command yang Dijalankan
```bash
python src/generators/generate_all.py
Invoke-RestMethod -Uri http://localhost:8091/api/pdf/sample-status
Invoke-RestMethod -Uri http://localhost:8091/api/data/source-status
```

## Hasil Validasi
- PDF sample tersedia dan metode ditandai `programmatic_text_extraction`.
- CSV transaksi terbaca 2 file, total 800 rows, semua kolom wajib ada.
- Excel RAB terbaca pada sheet `RAB` dan terdeteksi wide format untuk unpivot Silver.

## Masalah / Risiko
Jika sample PDF tidak ikut dibagikan, endpoint akan mengembalikan missing tanpa crash.

## Keputusan Teknis
Status CSV hanya menghitung `transaksi_*.csv` agar file upload dummy uji coba tidak mengubah total kontrol 800 rows.

## Langkah Berikutnya
Memastikan Quality Gate API tetap sesuai target 800/784/16.

## Status
Selesai
