# CHECKPOINT-05: Gold Layer

## Ringkasan

Gold layer berhasil dibentuk sebagai star schema, dimuat ke Iceberg catalog penuh di MinIO, dan tetap dimuat ke PostgreSQL schema `gold` sebagai fallback kompatibilitas.

## File Dibuat/Diubah

- `src/transformations/gold_star_schema.py`
- `src/sql/create_gold_tables.sql`
- `src/sql/trino_validation_queries.sql`
- `src/sql/superset_datasets.sql`
- `src/sql/load_gold_to_postgres.py`
- `src/transformations/load_gold_iceberg.py`
- `config/trino/catalog/iceberg.properties`
- `config/trino/catalog/postgres.properties`
- `data/generated/gold/*.csv`

## Command Dijalankan

```powershell
python src/transformations/gold_star_schema.py
python src/metrics/reconcile_control_total.py
python src/sql/load_gold_to_postgres.py
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
docker exec keuangan-trino trino --catalog iceberg --schema gold --execute "SELECT SUM(nominal_piutang_rp) AS total_piutang, COUNT(*) AS jumlah_penunggak FROM fact_piutang_ukt_prodi f JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key WHERE o.nama_prodi = 'Sains Data'"
```

## Status Validasi

- Fact rows: 803.
- Dashboard view rows: 803.
- Total piutang Sains Data: 31250000.
- Jumlah penunggak Sains Data: 15.
- Iceberg Gold tables: 6.
- Trino Iceberg query result: `"31250000","15"`.

## Langkah Berikutnya

CHECKPOINT-06 Airflow DAG.
