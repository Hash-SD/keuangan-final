# CHECKPOINT-DATA-05: Quality Gate Update

## Tujuan
Menyesuaikan quality gate dengan struktur transaksi UKT/SPI.

## File Dibaca
- src/validation/quality_gate.py
- data/generated/master_ukt_itera.csv
- data/generated/master_spi_itera.csv

## Dokumentasi Context7 yang Dibaca
- Python/cpython: csv dan pathlib.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- src/validation/quality_gate.py

## Implementasi
Validasi baru:
- `transaction_id` dan `nim_dummy` wajib ada
- tanggal valid
- semester Ganjil/Genap
- jenis biaya UKT/SPI
- prodi/fakultas sesuai referensi
- nominal tagihan sesuai UKT/SPI
- nominal bayar numerik
- status bayar valid

## Command yang Dijalankan
```bash
python src/validation/quality_gate.py
```

## Hasil Validasi
- total_rows = 800
- valid_rows = 784
- rejected_rows = 16
- dropout_rate = 2.0

## Masalah / Risiko
Tidak ada.

## Keputusan Teknis
Jika master biaya belum ada, quality gate memanggil generator master biaya.

## Langkah Berikutnya
Update Bronze/Silver/Gold.

## Status
Selesai
