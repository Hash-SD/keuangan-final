# CHECKPOINT-02: Docker Stack

## Ringkasan

Konfigurasi Docker Compose awal telah dibuat dan lolos validasi statis `docker compose config`. Runtime stack belum bisa dinyalakan karena Docker Desktop engine tidak aktif pada saat eksekusi.

## File Dibuat/Diubah

- `docker-compose.yml`
- `.env.example`
- `config/trino/catalog/iceberg.properties`
- `config/spark/spark-defaults.conf`
- `config/airflow/airflow.cfg`
- `config/superset/superset_config.py`

## Command Dijalankan

```powershell
docker --version
docker compose version
docker compose config
docker compose up -d
```

## Hasil Validasi

- Docker CLI tersedia: Docker version 28.4.0.
- Docker Compose tersedia: v2.39.2-desktop.1.
- `docker compose config` berhasil.
- `docker compose up -d` gagal karena Docker Desktop Linux engine belum berjalan.

## Error dan Solusi

Error:

```text
unable to get image 'trinodb/trino:474': error during connect:
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Solusi:

1. Jalankan Docker Desktop.
2. Pastikan status Docker Desktop sudah running.
3. Dari folder repo, jalankan:

```powershell
docker compose up -d
docker compose ps
```

## Status Validasi

- Compose static validation: lulus.
- Service runtime active: pending.
- Healthcheck runtime: pending.

## Langkah Berikutnya

Setelah Docker Desktop aktif, ulangi `docker compose up -d`. Jika semua service sehat, lanjutkan update checkpoint ini menjadi selesai dan baru masuk CHECKPOINT-03 Bronze Layer.

