# CHECKPOINT-E2E-05 - Medallion Pipeline

Tanggal: 2026-05-28
Status: PASS dengan catatan

## Perintah

```powershell
python src\transformations\bronze_ingest.py
python src\transformations\silver_clean.py
python src\transformations\gold_star_schema.py
```

## Output Command

Bronze:

```text
batch_id=batch-dummy-20260526
bronze_files=8
```

Silver:

```text
piutang_rows=803
kualitas_rows=4
transaction_rows=784
rab_rows=60
master_ukt_rows=328
master_spi_rows=41
```

Gold:

```text
fact_rows=803
dashboard_rows=803
```

## Validasi File

Bronze:

```text
data/generated/bronze/ingestion_metadata.json: True
```

Silver:

```text
data/generated/silver/fact_piutang_ukt_prodi.csv: True
data/generated/silver/transactions_clean.csv: True
data/generated/silver/rab_prodi_sains_data_long.csv: True
```

Gold:

```text
data/generated/gold/dim_organisasi.csv: True
data/generated/gold/dim_mahasiswa.csv: True
data/generated/gold/dim_kualitas_piutang.csv: True
data/generated/gold/dim_waktu_tunggakan.csv: True
data/generated/gold/fact_piutang_ukt_prodi.csv: True
data/generated/gold/vw_dashboard_piutang_ukt.csv: True
```

## Row Count

```text
data/generated/silver/fact_piutang_ukt_prodi.csv rows=803
data/generated/silver/transactions_clean.csv rows=784
data/generated/silver/rab_prodi_sains_data_long.csv rows=60
data/generated/gold/dim_organisasi.csv rows=41
data/generated/gold/dim_mahasiswa.csv rows=803
data/generated/gold/dim_kualitas_piutang.csv rows=4
data/generated/gold/dim_waktu_tunggakan.csv rows=32
data/generated/gold/fact_piutang_ukt_prodi.csv rows=803
data/generated/gold/vw_dashboard_piutang_ukt.csv rows=803
```

## Catatan

Bronze mengingest 8 file karena folder raw saat ini juga berisi file dummy upload selain file utama:

- `dummy_upload.pdf`
- `dummy_upload.csv`
- `dummy_upload.xlsx`

Semua metadata Bronze tetap menandai data sebagai dummy dan `contains_real_personal_data=False`. Dampak row count akan dipantau pada checkpoint metrics dan rekonsiliasi.

## Acceptance

- Bronze menyimpan raw/as-is metadata: PASS.
- Silver berisi data clean/unpivot: PASS.
- Gold membentuk star schema: PASS.
- Semua file wajib terbentuk: PASS.
- Tidak ada error eksekusi: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-06-metrics-validation.md`.
