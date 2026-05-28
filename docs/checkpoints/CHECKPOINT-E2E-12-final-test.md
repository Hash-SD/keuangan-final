# CHECKPOINT-E2E-12 - Final Test

Tanggal: 2026-05-28
Status: PASS

## Pytest

Perintah:

```powershell
python -m pytest tests\ -v
```

Hasil:

```text
collected 8 items
8 passed in 1.06s
```

Test yang lolos:

```text
tests/test_dummy_data.py::test_piutang_sains_data_control_total PASSED
tests/test_dummy_data.py::test_csv_transactions_shape_and_invalid_rate PASSED
tests/test_dummy_data.py::test_rab_control_total PASSED
tests/test_metrics.py::test_data_quality_score_perfect_for_controlled_dummy_data PASSED
tests/test_quality_gate.py::test_quality_gate_summary_exists PASSED
tests/test_reconciliation.py::test_reconciliation_passes PASSED
tests/test_reference_data.py::test_master_ukt_spi_reference_shapes PASSED
tests/test_reference_data.py::test_master_biaya_excel_sheets PASSED
```

## Full Basic Manual

Perintah dijalankan berurutan:

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
```

Hasil kontrol:

```text
total_rows=800
valid_rows=784
rejected_rows=16
dropout_rate=2.0
fact_rows=803
dashboard_rows=803
total_piutang=31250000
jumlah_penunggak=15
status=pass
```

Catatan: `fact_rows=803` karena folder raw berisi file dummy upload tambahan. Kontrol Sains Data tetap PASS dan semua file bertanda dummy.

## PostgreSQL, Iceberg, Superset Refresh

Perintah:

```powershell
python src\sql\load_gold_to_postgres.py
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
python src\sql\setup_superset_assets.py
python src\sql\setup_superset_dashboard.py
```

Hasil ringkas:

```text
loaded gold tables to postgres
wrote iceberg.gold.dim_organisasi: 41 rows
wrote iceberg.gold.dim_mahasiswa: 803 rows
wrote iceberg.gold.dim_kualitas_piutang: 4 rows
wrote iceberg.gold.dim_waktu_tunggakan: 32 rows
wrote iceberg.gold.fact_piutang_ukt_prodi: 803 rows
wrote iceberg.gold.vw_dashboard_piutang_ukt: 803 rows
database_id=2
dataset_id=1
dashboard_id=1
chart_ids=[1,2,3,4,5,6]
```

Trino query kontrol:

```text
"31250000","15"
```

## Port Check

Perintah:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_ports.ps1
```

Hasil:

```text
OK TCP  PostgreSQL metastore localhost:5432
OK HTTP MinIO API http://localhost:9000/minio/health/live -> 200
OK HTTP MinIO Console http://localhost:9001 -> 200
OK HTTP Spark Master UI http://localhost:8080 -> 200
OK HTTP Spark Worker UI http://localhost:8081 -> 200
OK TCP  Spark Master RPC localhost:7077
OK HTTP Airflow Webserver http://localhost:8085/health -> 200
OK HTTP Trino http://localhost:8082/v1/info -> 200
OK HTTP Superset http://localhost:8089/health -> 200
OK HTTP Portal Lokal http://localhost:8090 -> 200
```

Backend health:

```text
HTTP 200 {"basis":"main.pdf","mode":"local-on-premise","service":"portal-backend","status":"ok"}
```

Superset health:

```text
HTTP 200 OK
```

## Browser Final Check

URL:

```text
http://localhost:8090/#dashboard
```

Hasil:

```text
title="Portal Keuangan - Dashboard"
textHasQuality=True
textHasDropout=True
textHasPass=True
finalConsoleErrors=[]
```

## Final Acceptance

```text
[x] Docker compose up sukses.
[x] Semua port service lolos.
[x] Data dummy generate sukses.
[x] Quality gate sukses.
[x] Bronze sukses.
[x] Silver sukses.
[x] Gold sukses.
[x] Metrics sukses.
[x] Reconcile total PASS.
[x] PostgreSQL load sukses.
[x] Iceberg load sukses.
[x] Trino online.
[x] Superset online.
[x] Portal frontend online.
[x] Backend API online.
[x] UI membaca backend.
[x] UAT dummy bisa diisi.
[x] Tests pytest lolos.
[x] Tidak ada data pribadi riil pada data dummy/sample yang dicek.
[x] Tidak ada JS console error.
[x] Tidak ada broken link utama.
```

## Catatan

Tidak ada error blocking tersisa pada checkpoint final. Warning nonfatal yang muncul:

- Trino CLI: `Unable to create a system terminal, creating a dumb terminal`.
- Spark: `Unable to load native-hadoop library for your platform... using builtin-java classes where applicable`.

Keduanya tidak memblokir query, load Iceberg, atau validasi akhir.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-13-user-trial-guide.md`.
