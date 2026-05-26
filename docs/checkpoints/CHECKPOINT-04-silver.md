# CHECKPOINT-04: Silver Layer

## Ringkasan

Silver layer berhasil dibuat dari PDF, CSV valid, dan Excel RAB. PDF diekstrak tanpa OCR memakai `pdfplumber`; Excel RAB wide-format diubah menjadi long-format.

## File Dibuat/Diubah

- `src/extraction/extract_pdf_piutang.py`
- `src/transformations/silver_clean.py`
- `data/generated/silver/dim_kualitas_piutang.csv`
- `data/generated/silver/fact_piutang_ukt_prodi.csv`
- `data/generated/silver/transactions_clean.csv`
- `data/generated/silver/rab_prodi_sains_data_long.csv`
- `outputs/metrics/master_control_total.json`
- `outputs/metrics/pdf_extraction_log.json`

## Command Dijalankan

```powershell
python src/transformations/silver_clean.py
```

## Status Validasi

- Piutang rows: 803.
- Dim kualitas rows: 4.
- Transaction clean rows: 784.
- RAB long rows: 60.

## Langkah Berikutnya

CHECKPOINT-05 Gold Layer.

