# CHECKPOINT-03: Bronze Layer

## Ringkasan

Bronze layer berhasil dibuat di `data/generated/bronze` dengan salinan raw PDF/CSV/Excel dan metadata ingestion. Data invalid CSV dipisahkan oleh quality gate ke quarantine.

## File Dibuat/Diubah

- `src/validation/quality_gate.py`
- `src/transformations/bronze_ingest.py`
- `data/generated/bronze/ingestion_metadata.json`
- `data/quarantine/logs/rejected_rows.csv`
- `data/quarantine/logs/quality_gate_summary.json`

## Command Dijalankan

```powershell
python src/validation/quality_gate.py
python src/transformations/bronze_ingest.py
```

## Status Validasi

- Total transaksi masuk: 800.
- Valid transaksi: 784.
- Rejected rows: 16.
- Dropout rate: 2.0%.
- Bronze metadata tersedia.

## Langkah Berikutnya

CHECKPOINT-04 Silver Layer.

