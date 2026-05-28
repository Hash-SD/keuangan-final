# CHECKPOINT-E2E-03 - Data Generation

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
python src\generators\generate_all.py
```

## Output Generator

Generator menghasilkan:

```text
data\generated\master_ukt_itera.csv
data\generated\master_spi_itera.csv
data\generated\dummy_mahasiswa_itera.csv
data\raw\excel\master_biaya_itera.xlsx
data\raw\pdf\ITERA_LKTA2024Audited.pdf
data\raw\csv\transaksi_ganjil.csv
data\raw\csv\transaksi_genap.csv
data\raw\excel\rab_prodi_sains_data.xlsx
```

## Validasi File

```text
data/samples/ITERA_LKTA2024Audited.pdf: True
data/raw/pdf/ITERA_LKTA2024Audited.pdf: True
data/raw/csv/transaksi_ganjil.csv: True
data/raw/csv/transaksi_genap.csv: True
data/raw/excel/rab_prodi_sains_data.xlsx: True
data/generated/dummy_piutang_master.csv: True
data/generated/master_ukt_itera.csv: True
data/generated/master_spi_itera.csv: True
```

## Validasi Kontrol Dummy

- `transaksi_ganjil.csv`: 400 rows.
- `transaksi_genap.csv`: 400 rows.
- Total CSV transaksi: 800 rows.
- `master_ukt_itera.csv`: 328 rows.
- `master_spi_itera.csv`: 41 rows.
- `dummy_mahasiswa_itera.csv`: 410 rows.
- `rab_prodi_sains_data.xlsx` total `total_pagu`: Rp150.000.000.

Contoh nama mahasiswa memakai pola dummy:

```text
Mahasiswa Dummy 001
Mahasiswa Dummy 002
Mahasiswa Dummy 003
```

## Acceptance

- Data dummy berhasil dibuat: PASS.
- CSV transaksi total sekitar 800 rows: PASS, tepat 800.
- Semua data mahasiswa dummy dari sample yang dicek: PASS.
- Tidak ada indikasi data pribadi riil pada sample yang dicek: PASS.
- Excel RAB total pagu Rp150.000.000: PASS.
- Master UKT 328 rows: PASS.
- Master SPI 41 rows: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-04-quality-gate.md`.
