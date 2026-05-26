# CHECKPOINT-01: Dummy Data

## Ringkasan

Data dummy deterministik untuk PDF laporan audited, CSV transaksi, dan Excel RAB telah dibuat. Generator memakai seed tetap dan semua data mahasiswa bersifat dummy.

## File Dibuat/Diubah

- `requirements.txt`
- `src/common/paths.py`
- `src/generators/generate_all.py`
- `src/generators/generate_pdf_audited.py`
- `src/generators/generate_csv_transactions.py`
- `src/generators/generate_excel_rab.py`
- `tests/test_dummy_data.py`
- `data/raw/pdf/ITERA_LKTA2024Audited.pdf`
- `data/raw/csv/transaksi_ganjil.csv`
- `data/raw/csv/transaksi_genap.csv`
- `data/raw/excel/rab_prodi_sains_data.xlsx`
- `data/generated/dummy_piutang_master.csv`

## Command Dijalankan

```powershell
python -m pip install -r requirements.txt
python src/generators/generate_all.py
python -m pytest tests/test_dummy_data.py -v
```

## Output Data

- PDF digital-born: `data/raw/pdf/ITERA_LKTA2024Audited.pdf`
- CSV transaksi: 800 baris total, terbagi ganjil dan genap.
- Excel RAB: `data/raw/excel/rab_prodi_sains_data.xlsx`, sheet `RAB` dan `metadata`.
- Master piutang dummy untuk validasi: `data/generated/dummy_piutang_master.csv`

## Error dan Solusi

- `pytest` tidak tersedia di PATH PowerShell; solusi: gunakan `python -m pytest`.
- `reportlab.SimpleDocTemplate.build()` tidak menerima argumen `title` dan `author`; solusi: set metadata di atribut dokumen sebelum `build()`.
- Distribusi nominal contoh pada plan berjumlah 31500000, tetapi nilai kontrol wajib adalah 31250000. Solusi: acceptance criteria diprioritaskan; nominal mahasiswa Sains Data terakhir dibuat 3750000 agar total tepat.

## Status Validasi

Validasi otomatis lulus:

```text
tests/test_dummy_data.py::test_piutang_sains_data_control_total PASSED
tests/test_dummy_data.py::test_csv_transactions_shape_and_invalid_rate PASSED
tests/test_dummy_data.py::test_rab_control_total PASSED
3 passed
```

Validasi kontrol:

- Total baris PDF/master piutang: 803.
- Jumlah mahasiswa penunggak Sains Data: 15.
- Total piutang Sains Data: 31250000.
- Total transaksi CSV: 800.
- Invalid row rate CSV: 1-3%.
- Total pagu RAB: 150000000.
- PDF dapat dibaca `pdfplumber` dan memuat teks `Laporan Realisasi Anggaran`, `Tabel 1 Kriteria Piutang`, serta kontrol PNBP.

## Langkah Berikutnya

Lanjut CHECKPOINT-02: membuat `docker-compose.yml`, konfigurasi service MinIO, Spark, Airflow, Trino, Superset, PostgreSQL metastore, healthcheck, volume, dan port sesuai plan.

