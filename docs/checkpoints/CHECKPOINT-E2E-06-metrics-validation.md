# CHECKPOINT-E2E-06 - Metrics Validation

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
python src\metrics\reconcile_control_total.py
python src\metrics\pipeline_latency.py
python src\metrics\data_freshness.py
python src\metrics\dropout_rate.py
python src\metrics\data_quality_score.py
python src\metrics\generate_uat.py
```

## Output Utama

`reconcile_control_total.py`:

```text
{'total_piutang': 31250000, 'jumlah_penunggak': 15, 'target_total_piutang': 31250000, 'target_jumlah_penunggak': 15, 'status': 'pass'}
```

## Validasi File Metrics

```text
outputs/metrics/reconcile_control_total.json: True
outputs/metrics/pipeline_latency.json: True
outputs/metrics/data_freshness.json: True
outputs/metrics/dropout_rate.json: True
outputs/metrics/data_quality_score.json: True
```

## Isi Ringkas

Rekonsiliasi:

```json
{
  "total_piutang": 31250000,
  "jumlah_penunggak": 15,
  "target_total_piutang": 31250000,
  "target_jumlah_penunggak": 15,
  "status": "pass"
}
```

Dropout:

```json
{
  "total_rows": 800,
  "valid_rows": 784,
  "rejected_rows": 16,
  "dropout_rate": 2.0
}
```

Data Quality Score:

```json
{
  "completeness": 100.0,
  "validity": 100.0,
  "consistency": 100.0,
  "accuracy": 100.0,
  "data_quality_score": 100.0
}
```

Latency dan freshness terbentuk dengan nilai:

```text
latency_seconds=167769
freshness_seconds=167769
```

## UAT Output

`generate_uat.py` menulis output ke `outputs/uat/`, bukan `outputs/metrics/`:

```text
outputs/uat/uat_dummy_response.csv
outputs/uat/uat_score_summary.json
outputs/uat/uat_template.csv
```

## Acceptance

- Semua metrics JSON wajib terbentuk: PASS.
- Reconcile control total PASS: PASS.
- Total piutang UKT Rp31.250.000: PASS.
- Mahasiswa penunggak 15: PASS.
- Data Quality Score 100%: PASS.
- Dropout Rate berdasarkan rejected rows: PASS.
- Pipeline Latency ada: PASS.
- Data Freshness ada: PASS.
- UAT dummy terbentuk: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-07-postgres-iceberg-trino.md`.
