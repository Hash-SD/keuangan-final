# CHECKPOINT-00: Setup Awal

## Ringkasan

Setup awal repository telah dibuat berdasarkan rencana end-to-end. Struktur folder utama, file operasional dasar, diagram awal, dan catatan Context7 tersedia.

## File Dibuat/Diubah

- `README.md`
- `.env.example`
- `.gitignore`
- `Makefile`
- `docs/architecture.md`
- `docs/context7-notes/*.md`
- `docs/diagrams/flowchart.mmd`
- `docs/diagrams/star-schema.mmd`
- `docs/diagrams/architecture.mmd`
- Struktur folder `config/`, `data/`, `src/`, `dags/`, `tests/`, dan `outputs/`

## Command Dijalankan

```powershell
npx skills add https://github.com/vercel-labs/skills --skill find-skills
npx skills find "docker compose data engineering"
npx skills find "apache airflow dag"
npx skills find "spark etl python"
npx skills find "minio s3 object storage"
npx skills find "apache iceberg trino"
npx skills find "superset dashboard"
npx skills find "data quality validation synthetic data generation python"
npx skills add wshobson/agents@airflow-dag-patterns -g -y
npx skills add jeffallan/claude-skills@spark-engineer -g -y
npx skills add hamelsmu/evals-skills@generate-synthetic-data -g -y
```

## Skill Finder

- `find-skills` berhasil dipasang.
- Skill relevan yang dipasang:
  - `airflow-dag-patterns` untuk DAG orchestration.
  - `spark-engineer` untuk transformasi Spark.
  - `generate-synthetic-data` untuk data dummy deterministik.
- Skill dengan install count rendah dicatat sebagai referensi ringan: Docker Compose, MinIO, Superset, dan data quality.
- Tidak ditemukan skill kuat untuk gabungan `apache iceberg trino`, sehingga implementasi akan mengikuti dokumentasi Context7.

## Context7

Dokumentasi Context7 dibaca untuk:

- Docker Compose
- Apache Airflow
- Apache Spark
- MinIO Python SDK
- Apache Iceberg
- Trino
- Apache Superset
- pdfplumber
- pandas

Ringkasannya tersimpan di `docs/context7-notes/`.

## Error dan Solusi

- Tidak ada error blocking.
- Hasil pencarian skill untuk `apache iceberg trino` kosong; mitigasi: gunakan Context7 resmi Iceberg dan Trino.

## Status Validasi

- Struktur folder utama tersedia.
- File dasar tersedia.
- Context7 notes awal tersedia.
- CHECKPOINT-00 selesai.

## Langkah Berikutnya

Lanjut CHECKPOINT-01: membuat generator data dummy PDF/CSV/Excel deterministik, lalu validasi nilai kontrol:

- PDF 803 baris, termasuk 15 mahasiswa Sains Data.
- Total piutang Sains Data = 31250000.
- CSV ganjil/genap sekitar 800 transaksi dengan 1-3% data invalid.
- Excel RAB total pagu = 150000000.

