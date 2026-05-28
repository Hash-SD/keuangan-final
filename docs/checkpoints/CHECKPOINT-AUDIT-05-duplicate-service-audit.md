# CHECKPOINT-AUDIT-05: Duplicate Service Audit

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
docker ps -a
docker compose ps
docker network ls
docker volume ls
docker compose config
Get-NetTCPConnection -LocalPort 8080,8081,8082,8085,8089,9000,9001,5432,7077,8090,8091 -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "ProcessId=19932 OR ProcessId=19944"
```

## Container Aktif

Container aktif hanya dari project `keuangan-final`:

```text
keuangan-spark-worker
keuangan-spark-master
keuangan-superset
keuangan-airflow-webserver
keuangan-airflow-scheduler
keuangan-trino
keuangan-postgres-metastore
keuangan-minio
```

Init-only:

```text
keuangan-airflow-init Exited (0)
keuangan-minio-init   Exited (0)
```

Tidak ada container aktif lain dengan nama mirip yang mem-publish port audit.

## Network

```text
bridge
host
lakehouse_net
none
```

Hanya `lakehouse_net` yang relevan untuk project ini. Tidak ada duplicate active network yang dipakai stack ini.

## Volume

Volume aktif project ini:

```text
keuangan-final_airflow_logs
keuangan-final_minio_data
keuangan-final_postgres_metastore_data
keuangan-final_spark_warehouse
keuangan-final_superset_home
```

Volume lama terdeteksi tetapi tidak dipakai container aktif saat audit:

```text
uc-data-lakehouse_airflow_data
uc-data-lakehouse_airflow_logs
uc-data-lakehouse_hive_metastore_data
uc-data-lakehouse_minio_data
uc-data-lakehouse_portal_uploads
uc-data-lakehouse_postgres_data
uc-data-lakehouse_spark_data
uc-data-lakehouse_spark_worker_data
uc-data-lakehouse_superset_home
uc-data-lakehouse_trino_data
```

Sesuai aturan audit, volume lama tidak dihapus tanpa konfirmasi. Karena tidak ada container aktif dari project lama, volume tersebut tidak menyebabkan port collision.

## Port Collision

Port audit:

```text
5432, 7077, 8080, 8081, 8082, 8085, 8089, 9000, 9001
```

Listener Docker muncul pada IPv6 wildcard dan loopback melalui proses Docker Desktop. Ini normal untuk published port Docker Desktop, bukan service duplicate aplikasi.

Port lokal:

```text
8090 -> python portal/server.py
8091 -> python -m portal_backend.app
```

Command line:

```text
19932 "python.exe" C:\Users\hm\keuangan-final\portal\server.py
19944 "python.exe" -m portal_backend.app
```

## Kesimpulan

- Tidak ada dua portal frontend aktif pada port 8090.
- Tidak ada dua backend aktif pada port 8091.
- Tidak ada dua Superset, Airflow webserver, Trino, MinIO, Spark, atau PostgreSQL aktif pada host port audit.
- Ada volume stale dari project lama `uc-data-lakehouse`, tetapi tidak aktif dan tidak mengganggu. Clean-up opsional hanya boleh dilakukan setelah konfirmasi pengguna.

## Acceptance

- Tidak ada duplicate service aktif: PASS.
- Tidak ada port collision blocking: PASS.
- Tidak ada container lama aktif yang mengganggu: PASS.
- Tidak ada penghapusan volume/container tanpa konfirmasi: PASS.
