# CHECKPOINT-DATA-06: Bronze Silver Gold Update

## Tujuan
Menyesuaikan layer Medallion untuk data referensi UKT/SPI.

## File Dibaca
- src/transformations/bronze_ingest.py
- src/transformations/silver_clean.py
- src/transformations/gold_star_schema.py

## Dokumentasi Context7 yang Dibaca
- Python/cpython: csv/pathlib.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- src/transformations/bronze_ingest.py
- src/transformations/silver_clean.py
- src/transformations/gold_star_schema.py

## Implementasi
- Bronze metadata mencatat `source_type`, `row_count`, `dummy_data`, dan `contains_real_personal_data`.
- Silver menghasilkan `silver_master_ukt.csv`, `silver_master_spi.csv`, `silver_mahasiswa.csv`, dan `silver_rab.csv`.
- Gold menghasilkan `dim_biaya_ukt.csv` dan `dim_biaya_spi.csv`.

## Command yang Dijalankan
```bash
python src/transformations/bronze_ingest.py
python src/transformations/silver_clean.py
python src/transformations/gold_star_schema.py
```

## Hasil Validasi
Gold tetap menjaga total piutang Sains Data Rp31.250.000 dan 15 penunggak.

## Masalah / Risiko
Bronze masih menyalin file upload dummy jika ada di `data/raw`; ini sesuai perilaku upload lokal.

## Keputusan Teknis
Dashboard tetap fokus pada Piutang UKT Prodi Sains Data.

## Langkah Berikutnya
API referensi backend.

## Status
Selesai
