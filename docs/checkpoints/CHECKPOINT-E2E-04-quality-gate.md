# CHECKPOINT-E2E-04 - Quality Gate

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
python src\validation\quality_gate.py
```

## Hasil

Output command:

```text
{'batch_id': 'batch-dummy-20260526', 'total_rows': 800, 'valid_rows': 784, 'rejected_rows': 16, 'dropout_rate': 2.0, 'created_at': '2026-05-28T08:35:06+00:00'}
```

## Validasi File

```text
data/quarantine/logs/quality_gate_summary.json: True
data/quarantine/logs/rejected_rows.csv: True
data/generated/bronze/csv_transactions_valid.csv: True
```

## Validasi Isi

`quality_gate_summary.json`:

```json
{
  "batch_id": "batch-dummy-20260526",
  "total_rows": 800,
  "valid_rows": 784,
  "rejected_rows": 16,
  "dropout_rate": 2.0,
  "created_at": "2026-05-28T08:35:06+00:00"
}
```

Row count:

```text
data/quarantine/logs/rejected_rows.csv rows=16
data/generated/bronze/csv_transactions_valid.csv rows=784
```

## Acceptance

- Quality gate sukses: PASS.
- Summary JSON valid: PASS.
- `total_rows = 800`: PASS.
- `valid_rows = 784`: PASS.
- `rejected_rows = 16`: PASS.
- `dropout_rate = 2%`: PASS.
- Invalid rows masuk quarantine: PASS.
- Valid rows masuk output valid: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-05-medallion-pipeline.md`.
