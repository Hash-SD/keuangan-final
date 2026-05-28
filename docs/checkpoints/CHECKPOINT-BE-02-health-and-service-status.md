# CHECKPOINT-BE-02: Health and Service Status

## Tujuan
Membuat endpoint status untuk service lokal lakehouse.

## File Dibaca
- docker-compose.yml
- README.md
- portal_backend/app.py

## Dokumentasi Context7 yang Dibaca
- Python/cpython: socket TCP dan pola exception handling.
- Python/cpython: request proses ringan dengan timeout.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada checkpoint BE-00.

## File Dibuat/Diubah
- portal_backend/services/system_status.py
- portal_backend/app.py

## Implementasi
Endpoint dibuat:
```text
GET /api/status/services
```

Service yang dicek:
- Portal Keuangan: `http://localhost:8090`
- Airflow: `http://localhost:8085`
- Superset: `http://localhost:8089`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Spark Master: `http://localhost:8080`
- Spark Worker: `http://localhost:8081`
- Trino: `http://localhost:8082/v1/info`
- PostgreSQL Metastore: `localhost:5432`

## Command yang Dijalankan
```bash
Invoke-RestMethod -Uri http://localhost:8091/api/status/services
```

## Hasil Validasi
Endpoint mengembalikan status `online`, `offline`, atau `unknown` tanpa crash saat Docker service tidak aktif.

## Masalah / Risiko
Jika banyak service offline, pengecekan HTTP tetap membutuhkan timeout singkat. Timeout dibuat kecil agar render frontend tidak lama.

## Keputusan Teknis
PostgreSQL dicek dengan socket TCP, bukan link browser.

## Langkah Berikutnya
Membuat API metrics.

## Status
Selesai
