# CHECKPOINT-E2E-07 - PostgreSQL, Iceberg, Trino

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
python src\sql\load_gold_to_postgres.py
docker exec keuangan-spark-master /opt/spark/bin/spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1,org.apache.iceberg:iceberg-aws-bundle:1.10.1,org.postgresql:postgresql:42.7.3 /opt/lakehouse/src/transformations/load_gold_iceberg.py
Invoke-WebRequest -Uri "http://localhost:8082/v1/info" -UseBasicParsing
```

## PostgreSQL Fallback

`load_gold_to_postgres.py` berhasil:

```text
loaded gold tables to postgres
```

Validasi PostgreSQL:

```text
fact_rows | total_piutang
803       | 1955550000
```

## Iceberg Load

Spark submit berhasil dengan exit code 0. Ringkasan output:

```text
wrote iceberg.gold.dim_organisasi: 41 rows
wrote iceberg.gold.dim_mahasiswa: 803 rows
wrote iceberg.gold.dim_kualitas_piutang: 4 rows
wrote iceberg.gold.dim_waktu_tunggakan: 32 rows
wrote iceberg.gold.fact_piutang_ukt_prodi: 803 rows
wrote iceberg.gold.vw_dashboard_piutang_ukt: 803 rows
```

## Trino Health

`http://localhost:8082/v1/info` mengembalikan HTTP 200 dengan Trino version `474`.

## Trino Query Validation

Query total fact:

```sql
SELECT COUNT(*) AS fact_rows, SUM(nominal_piutang_rp) AS total_piutang
FROM fact_piutang_ukt_prodi;
```

Hasil:

```text
"803","1955550000"
```

Query kontrol Sains Data:

```sql
SELECT SUM(f.nominal_piutang_rp) AS sains_data_total,
       COUNT(*) AS sains_data_penunggak
FROM fact_piutang_ukt_prodi f
JOIN dim_organisasi o ON f.organisasi_key = o.organisasi_key
WHERE o.nama_prodi = 'Sains Data';
```

Hasil:

```text
"31250000","15"
```

Catatan nonfatal dari CLI Trino:

```text
WARNING: Unable to create a system terminal, creating a dumb terminal
```

Query tetap berhasil dan menghasilkan output valid.

## Acceptance

- Gold bisa diload ke PostgreSQL fallback: PASS.
- Iceberg load sukses karena Docker Spark siap: PASS.
- Trino service online: PASS.
- Query count rows fact sukses: PASS.
- Query sum nominal piutang sukses: PASS.
- Query kontrol Sains Data menghasilkan Rp31.250.000 dan 15 penunggak: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-08-superset.md`.
