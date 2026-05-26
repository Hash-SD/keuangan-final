# CHECKPOINT-06: Airflow DAG

## Ringkasan

Airflow berjalan di Docker dan DAG `keuangan_prodi_lakehouse_dag` berhasil menjalankan pipeline dari generate data sampai metrik dan refresh placeholder Superset dataset.

## File Dibuat/Diubah

- `dags/keuangan_prodi_lakehouse_dag.py`
- `docker-compose.yml`
- `requirements.txt`

## Command Dijalankan

```powershell
docker compose up -d airflow-init airflow-webserver airflow-scheduler
docker exec keuangan-airflow-webserver airflow dags list
docker exec keuangan-airflow-webserver airflow dags unpause keuangan_prodi_lakehouse_dag
docker exec keuangan-airflow-webserver airflow dags trigger keuangan_prodi_lakehouse_dag
docker exec keuangan-airflow-webserver airflow tasks states-for-dag-run keuangan_prodi_lakehouse_dag manual__2026-05-26T09:20:28+00:00
```

## Error dan Solusi

- `extract_bronze` gagal saat `shutil.copy2()` mencoba menulis metadata timestamp pada bind mount Windows. Solusi: ubah ke `shutil.copyfile()`.

## Status Validasi

Run sukses:

```text
manual__2026-05-26T09:20:28+00:00 | success
```

Semua task utama success:

- generate_dummy_data
- quality_gate_process
- extract_bronze
- clean_silver
- load_gold_schema
- validate_mart
- calculate_metrics
- refresh_superset_dataset

## Langkah Berikutnya

CHECKPOINT-07 Trino dan Superset.

