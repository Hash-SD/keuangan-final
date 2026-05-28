# CHECKPOINT-DATA-01: Master UKT/SPI Generator

## Tujuan
Membuat generator master UKT, master SPI, dummy mahasiswa, dan Excel master biaya.

## File Dibaca
- src/generators/generate_pdf_audited.py
- src/generators/generate_all.py

## Dokumentasi Context7 yang Dibaca
- Python/cpython: pathlib dan csv.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- src/generators/master_biaya.py
- src/generators/generate_all.py
- tests/test_reference_data.py

## Implementasi
Generator menghasilkan:
- `data/generated/master_ukt_itera.csv`
- `data/generated/master_spi_itera.csv`
- `data/generated/dummy_mahasiswa_itera.csv`
- `data/raw/excel/master_biaya_itera.xlsx`

## Command yang Dijalankan
```bash
python src/generators/generate_all.py
```

## Hasil Validasi
- Master UKT: 328 rows
- Master SPI: 41 rows
- Sains Data Gol. 8: 9500000
- Sains Data SPI: 30000000
- Excel memiliki sheet `UKT_Wide`, `UKT_Long`, `SPI`, `Metadata`

## Masalah / Risiko
Tidak ada.

## Keputusan Teknis
Data prodi/UKT/SPI memakai struktur referensi dummy yang sudah ada pada generator PDF agar tidak duplikatif.

## Langkah Berikutnya
Menyesuaikan CSV transaksi.

## Status
Selesai
