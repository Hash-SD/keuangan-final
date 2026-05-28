# CHECKPOINT-E2E-09 - Portal Frontend

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
.\scripts\start_portal.ps1
.\scripts\start_portal_backend.ps1
```

Hasil:

```text
Portal lokal aktif: http://localhost:8090
Portal frontend aktif: http://localhost:8090
Portal backend aktif: http://localhost:8091/api/health
```

## Browser Validation

Portal dibuka di browser lokal:

```text
http://localhost:8090
```

Halaman yang divalidasi:

```text
Beranda     -> activeNav=beranda,     activePage=page-beranda
Data        -> activeNav=data,        activePage=page-data
Dashboard   -> activeNav=dashboard,   activePage=page-dashboard
Lakehouse   -> activeNav=lakehouse,   activePage=page-lakehouse
Orkestrasi  -> activeNav=orkestrasi,  activePage=page-orkestrasi
Analytics   -> activeNav=analytics,   activePage=page-analytics
System      -> activeNav=system,      activePage=page-system
```

Hasil browser:

- Sidebar kiri konsisten: PASS.
- Header konsisten: PASS.
- Footer global muncul: PASS.
- Active menu sesuai halaman: PASS.
- Tidak ada top navigation menu utama: PASS.
- Console error: PASS, kosong.
- PostgreSQL memakai `Copy Connection`: PASS.

Clipboard setelah klik tombol PostgreSQL:

```text
Host=localhost;Port=5432;Database=metastore;Username=lakehouse;Password=lakehouse
```

## Local Link Check

```text
OK 200 http://localhost:8090/#beranda
OK 200 http://localhost:8090/#data
OK 200 http://localhost:8090/#dashboard
OK 200 http://localhost:8090/#lakehouse
OK 200 http://localhost:8090/#orkestrasi
OK 200 http://localhost:8090/#analytics
OK 200 http://localhost:8090/#system
OK 200 http://localhost:8085/
OK 200 http://localhost:8089/
OK 200 http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/
OK 200 http://localhost:9001/
OK 200 http://localhost:8080/
OK 200 http://localhost:8081/
OK 200 http://localhost:8082/v1/info
OK 200 http://localhost:8091/api/health
```

## Acceptance

- Portal frontend berjalan: PASS.
- Semua halaman bisa dibuka: PASS.
- Tidak ada JS console error: PASS.
- Semua link lokal utama benar: PASS.
- PostgreSQL memakai Copy Connection, bukan Open browser: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-10-backend-api.md`.
