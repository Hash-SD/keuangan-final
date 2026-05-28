# CHECKPOINT-UI-10: System Page

## Tujuan
Membuat halaman System sebagai portal service lokal dan status infrastruktur.

## File Dibaca
- `portal/index.html`
- `portal/server.py`
- `README.md`
- `docker-compose.yml`
- `scripts/check_ports.ps1`
- `stitch_uc_data_portal_design/system_portal_keuangan_sidebar/code.html`

## Dokumentasi Context7 yang Dibaca
- Docker Compose: port mapping, healthcheck, service readiness.
- MDN Web Docs: Clipboard API untuk Copy Connection.

## Skill Finder
Command:
```bash
npx skills add https://github.com/vercel-labs/skills --skill find-skills
```

Status:
berhasil pada UI-00.

## File Dibuat/Diubah
- `portal/index.html`
- `portal/server.py`
- `docs/checkpoints/CHECKPOINT-UI-10-system-page.md`

## Implementasi
System memuat service card:
- Airflow `http://localhost:8085`, credential `airflow / airflow`.
- Superset `http://localhost:8089`, credential `admin / admin`.
- Superset Dashboard `http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/`.
- MinIO Console `http://localhost:9001`, API `http://localhost:9000`, credential `minioadmin / minioadmin`.
- Spark Master `http://localhost:8080`.
- Spark Worker `http://localhost:8081`.
- Trino `http://localhost:8082/v1/info`.
- PostgreSQL `localhost:5432`, credential `lakehouse / lakehouse`, DB `metastore`.
- Portal Keuangan `http://localhost:8090`.

PostgreSQL memakai tombol `Copy Connection`, bukan Open browser.

## Command yang Dijalankan
```bash
Select-String -Path portal/index.html -Pattern "8085|8089|9000|9001|8082|5432|Copy Connection"
```

## Hasil Validasi
- Semua service lokal tampil.
- Port sudah benar.
- PostgreSQL tidak memiliki link browser.
- Audit trail tersedia.

## Masalah / Risiko
- Status service tergantung service lokal yang sedang berjalan.

## Keputusan Teknis
- Status service dicek oleh `portal/server.py` via TCP socket dan fallback `Offline`.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-11-local-data-integration.md`.

## Status
Selesai
