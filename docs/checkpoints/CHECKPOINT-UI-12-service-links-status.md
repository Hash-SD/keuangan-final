# CHECKPOINT-UI-12: Service Links and Status

## Tujuan
Memastikan semua link dan status service lokal benar.

## File Dibaca
- `portal/index.html`
- `portal/server.py`
- `README.md`
- `docker-compose.yml`
- `scripts/check_ports.ps1`

## Dokumentasi Context7 yang Dibaca
- Docker Compose: port mapping dan healthcheck.

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
- `docs/checkpoints/CHECKPOINT-UI-12-service-links-status.md`

## Implementasi
Link yang dipakai:
- Portal: `http://localhost:8090`
- Airflow: `http://localhost:8085`
- Superset: `http://localhost:8089`
- Superset Dashboard: `http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Spark Master: `http://localhost:8080`
- Spark Worker: `http://localhost:8081`
- Trino: `http://localhost:8082/v1/info`
- PostgreSQL: `localhost:5432` via Copy Connection.

## Command yang Dijalankan
```bash
.\scripts\check_ports.ps1
```

## Hasil Validasi
- Browser assertion memastikan semua port wajib tampil pada System page.
- PostgreSQL tidak memiliki link `<a>`.
- `check_ports.ps1` gagal karena PostgreSQL lokal sedang offline: `PostgreSQL metastore failed on localhost:5432`.

## Masalah / Risiko
- Docker stack tidak sedang aktif penuh pada saat validasi, sehingga sebagian service tampil `Offline`.

## Keputusan Teknis
- UI menampilkan `Offline` tanpa error jika service tidak aktif.

## Langkah Berikutnya
Lanjut `CHECKPOINT-UI-13-responsive-polish.md`.

## Status
Selesai
