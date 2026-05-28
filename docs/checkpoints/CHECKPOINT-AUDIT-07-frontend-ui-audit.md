# CHECKPOINT-AUDIT-07: Frontend UI Audit

Tanggal: 2026-05-28
Status: Selesai

## URL

```text
http://localhost:8090
```

## Browser Audit

Halaman wajib:

```text
Beranda    -> activeNav=beranda,    activePage=page-beranda
Data       -> activeNav=data,       activePage=page-data
Dashboard  -> activeNav=dashboard,  activePage=page-dashboard
Lakehouse  -> activeNav=lakehouse,  activePage=page-lakehouse
Orkestrasi -> activeNav=orkestrasi, activePage=page-orkestrasi
Analytics  -> activeNav=analytics,  activePage=page-analytics
System     -> activeNav=system,     activePage=page-system
```

Console error final:

```text
[]
```

## Layout

- Sidebar kiri berisi 7 item dan konsisten: PASS.
- Header/page title konsisten: PASS.
- Tidak ada top nav lama di header: PASS.
- Footer global muncul: PASS.
- Footer fixed tidak menutupi konten terakhir ketika scroll sampai bawah: PASS.

Pengukuran halaman System di scroll bottom:

```text
footerTop=1118.4
lastSectionBottom=1038.3
lastSectionHidden=False
```

## System Page Port Evidence

System page sekarang membedakan service host port berikut:

```text
MinIO API: http://localhost:9000/minio/health/live
MinIO Console: http://localhost:9001
Spark Master UI: http://localhost:8080
Spark Master RPC: localhost:7077
Spark Worker UI: http://localhost:8081
Airflow: http://localhost:8085
Superset: http://localhost:8089
Trino: http://localhost:8082/v1/info
PostgreSQL Metastore: localhost:5432
Portal: http://localhost:8090
Portal Backend API: http://localhost:8091/api/health
```

Tidak ditemukan port salah:

```text
localhost:8088: false
localhost:8080/v1/info: false
http://localhost:8088: false
```

## Copy Connection

Tombol copy yang tersedia:

```text
Spark Master RPC -> spark://localhost:7077
PostgreSQL Metastore -> Host=localhost;Port=5432;Database=metastore;Username=lakehouse;Password=lakehouse
```

PostgreSQL tidak dibuat sebagai link browser: PASS.

## Link Audit

Semua link lokal utama mengembalikan HTTP 200:

```text
http://localhost:8090/#beranda
http://localhost:8090/#data
http://localhost:8090/#dashboard
http://localhost:8090/#lakehouse
http://localhost:8090/#orkestrasi
http://localhost:8090/#analytics
http://localhost:8090/#system
http://localhost:8085/
http://localhost:8089/
http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/
http://localhost:9000/minio/health/live
http://localhost:9001/
http://localhost:8080/
http://localhost:8081/
http://localhost:8082/v1/info
http://localhost:8090/
http://localhost:8091/api/health
```

## Backend Offline Fallback

Backend 8091 dihentikan sementara untuk simulasi. UI tetap render dengan fallback portal state.

System page menampilkan backend sebagai offline:

```text
Portal Backend API
Backend Lokal
Offline
Uptime
Belum terdeteksi
Port
8091
URL / Host
http://localhost:8091/api/health
```

Backend kemudian dinyalakan kembali dengan `scripts/start_portal_backend.ps1`.

## Acceptance

- Semua halaman bisa dibuka: PASS.
- Sidebar/header/footer konsisten: PASS.
- Active menu sesuai halaman: PASS.
- Tidak ada top nav lama: PASS.
- Tidak ada angka dummy salah pada dashboard: PASS.
- Tidak ada link port salah: PASS.
- System page membedakan MinIO API/Console, Spark UI/RPC, Airflow/Superset/Trino host ports: PASS.
- PostgreSQL hanya Copy Connection: PASS.
- Tidak ada JavaScript console error: PASS.
- Jika backend offline, UI fallback jelas pada System page: PASS.
