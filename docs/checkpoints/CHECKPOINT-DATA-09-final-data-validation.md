# CHECKPOINT-DATA-09: Final Data Validation

## Tujuan
Validasi akhir data dummy UKT/SPI, PDF sample, pipeline, backend API, dan test.

## File Dibaca
- data/generated/master_ukt_itera.csv
- data/generated/master_spi_itera.csv
- data/generated/dummy_mahasiswa_itera.csv
- data/raw/csv/transaksi_ganjil.csv
- data/raw/csv/transaksi_genap.csv
- data/raw/excel/master_biaya_itera.xlsx
- data/raw/excel/rab_prodi_sains_data.xlsx
- data/generated/gold/dim_biaya_ukt.csv
- data/generated/gold/dim_biaya_spi.csv

## Dokumentasi Context7 yang Dibaca
- Flask: endpoint.
- Python/cpython: csv/pathlib/subprocess.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil.

## File Dibuat/Diubah
- tests/test_reference_data.py

## Implementasi
Test tambahan dibuat untuk menjaga bentuk master UKT/SPI dan sheet Excel master biaya.

## Command yang Dijalankan
```bash
python src/generators/generate_all.py
python src/validation/quality_gate.py
python src/transformations/bronze_ingest.py
python src/transformations/silver_clean.py
python src/transformations/gold_star_schema.py
python src/metrics/reconcile_control_total.py
python src/metrics/data_quality_score.py
python -m pytest tests -v
```

## Hasil Validasi
- `master_ukt_itera.csv`: 328 rows
- `master_spi_itera.csv`: 41 rows
- `master_biaya_itera.xlsx`: sheet `UKT_Wide`, `UKT_Long`, `SPI`, `Metadata`
- RAB total: 150000000
- Transaksi: 800 rows
- Rejected rows: 16
- Valid rows: 784
- Gold control total: Rp31.250.000 dan 15 penunggak
- `python -m pytest tests -v`: 8 passed

## Masalah / Risiko
PDF sample lokal tetap untracked dan harus tersedia di `data/samples/` jika ingin status available pada mesin lain.

## Keputusan Teknis
Semua data mahasiswa dan transaksi tetap dummy.

## Langkah Berikutnya
Opsional: tambahkan validasi browser visual jika tooling browser tersedia.

## Status
Selesai
