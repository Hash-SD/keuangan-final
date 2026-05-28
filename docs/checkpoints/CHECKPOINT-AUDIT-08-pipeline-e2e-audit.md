# CHECKPOINT-AUDIT-08: Pipeline E2E Audit

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
python src\generators\generate_all.py
python src\validation\quality_gate.py
python src\transformations\bronze_ingest.py
python src\transformations\silver_clean.py
python src\transformations\gold_star_schema.py
python src\metrics\reconcile_control_total.py
python src\metrics\pipeline_latency.py
python src\metrics\data_freshness.py
python src\metrics\dropout_rate.py
python src\metrics\data_quality_score.py
python src\metrics\generate_uat.py
python -m pytest tests\ -v
```

## Pipeline Output

Generator:

```text
data/generated/master_ukt_itera.csv
data/generated/master_spi_itera.csv
data/generated/dummy_mahasiswa_itera.csv
data/raw/excel/master_biaya_itera.xlsx
data/raw/pdf/ITERA_LKTA2024Audited.pdf
data/raw/csv/transaksi_ganjil.csv
data/raw/csv/transaksi_genap.csv
data/raw/excel/rab_prodi_sains_data.xlsx
```

Quality gate:

```text
total_rows=800
valid_rows=784
rejected_rows=16
dropout_rate=2.0
```

Bronze:

```text
ingestion_metadata.json tersedia
files=8
```

Catatan: folder raw juga berisi `dummy_upload.*` dari uji upload sebelumnya. Metadata Bronze tetap menandai file sebagai dummy dan tidak mengandung data pribadi riil.

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

Rekonsiliasi:

```text
total_piutang=31250000
jumlah_penunggak=15
target_total_piutang=31250000
target_jumlah_penunggak=15
status=pass
```

Data quality:

```text
completeness=100.0
validity=100.0
consistency=100.0
accuracy=100.0
data_quality_score=100.0
```

## Validasi File

```text
data/samples/ITERA_LKTA2024Audited.pdf True
data/raw/pdf/ITERA_LKTA2024Audited.pdf True
data/raw/csv/transaksi_ganjil.csv True
data/raw/csv/transaksi_genap.csv True
data/raw/excel/rab_prodi_sains_data.xlsx True
data/quarantine/logs/quality_gate_summary.json True
data/quarantine/logs/rejected_rows.csv True
data/generated/bronze/ingestion_metadata.json True
data/generated/silver/fact_piutang_ukt_prodi.csv True
data/generated/silver/transactions_clean.csv True
data/generated/silver/rab_prodi_sains_data_long.csv True
data/generated/gold/fact_piutang_ukt_prodi.csv True
data/generated/gold/vw_dashboard_piutang_ukt.csv True
outputs/metrics/reconcile_control_total.json True
outputs/metrics/pipeline_latency.json True
outputs/metrics/data_freshness.json True
outputs/metrics/dropout_rate.json True
outputs/metrics/data_quality_score.json True
outputs/uat/uat_dummy_response.csv True
outputs/uat/uat_score_summary.json True
```

## Dummy Data Check

Sample nama mahasiswa:

```text
Mahasiswa Dummy 001
Mahasiswa Dummy 002
Mahasiswa Dummy 003
Mahasiswa Dummy 004
Mahasiswa Dummy 005
```

Tidak ada data pribadi riil pada sample dummy yang dicek.

## Pytest

```text
collected 8 items
8 passed in 0.70s
```

## Acceptance

- Semua script sukses: PASS.
- PDF sample status jelas: PASS.
- CSV transaksi total 800: PASS.
- Quality gate rejected rows 16: PASS.
- Valid rows 784: PASS.
- Bronze metadata ada: PASS.
- Silver output ada: PASS.
- Gold star schema ada: PASS.
- Total piutang UKT Sains Data Rp31.250.000: PASS.
- Jumlah penunggak Sains Data 15: PASS.
- Data Quality Score ada dan 100: PASS.
- Dropout Rate ada dan 2%: PASS.
- Pipeline Latency ada: PASS.
- Data Freshness ada: PASS.
- UAT dummy ada: PASS.
- Pytest lolos: PASS.
- Tidak ada data pribadi riil pada sample yang dicek: PASS.
