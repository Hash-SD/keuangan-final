# CHECKPOINT-E2E-11 - UI Backend Integration

Tanggal: 2026-05-28
Status: PASS setelah perbaikan kecil UI

## Perbaikan

Saat validasi awal, halaman Orkestrasi belum memiliki tombol `Validate Gold`. File yang diperbaiki:

```text
portal/index.html
```

Perubahan:

- Label tombol pipeline dibuat eksplisit: `Run Quality Gate`, `Run Bronze`, `Run Silver`, `Run Gold`, `Run Metrics`.
- Tombol `Validate Gold` ditambahkan dengan `data-pipeline="validate-gold"`.

## Validasi Halaman Membaca Backend

Browser validation:

```text
Dashboard  -> Data Quality Score 100%, Dropout Rate 2%, Rejected Rows 16, Gold Validation PASS
System     -> service status online, termasuk Portal Backend API dan PostgreSQL Metastore
Data       -> PDF Audited ready, CSV Transaksi 800/800 rows, Excel RAB ready, rejected rows tampil
Lakehouse  -> Bronze/Silver/Gold ready, Validate Gold PASS
Analytics  -> UAT Score Summary 4.6, kategori Sangat baik, 15 responden
```

Console error setelah validasi: kosong.

## Validasi Tombol Orkestrasi

Tombol wajib yang ditemukan:

```text
Run Quality Gate  -> data-pipeline=quality-gate
Run Bronze        -> data-pipeline=bronze
Run Silver        -> data-pipeline=silver
Run Gold          -> data-pipeline=gold
Validate Gold     -> data-pipeline=validate-gold
Run Metrics       -> data-pipeline=metrics
Full Run Basic    -> data-pipeline=full-run-basic
```

Hasil klik dari browser:

```text
quality-gate    loadingSeen=True successSeen=True lastAction="quality-gate: success"
bronze          loadingSeen=True successSeen=True lastAction="bronze: success"
silver          loadingSeen=True successSeen=True lastAction="silver: success"
gold            loadingSeen=True successSeen=True lastAction="gold: success"
validate-gold   loadingSeen=True successSeen=True lastAction="validate-gold: success"
full-run-basic  loadingSeen=True successSeen=True lastAction="full-run-basic: success"
```

## Error State

Error state diuji dengan simulasi terkendali:

1. Backend 8091 dihentikan sementara.
2. Tombol `Run Quality Gate` diklik.
3. UI menampilkan toast:

```text
Failed to fetch
```

4. Tombol kembali enabled.
5. Backend dinyalakan kembali dengan `scripts/start_portal_backend.ps1`.

## UAT Submit

Halaman Analytics:

```text
Submit UAT dummy loadingSeen=True
Toast="UAT dummy terkirim"
Console error kosong
```

## Acceptance

- Dashboard membaca `/api/metrics`: PASS.
- System membaca `/api/status/services`: PASS.
- Data membaca `/api/pdf/sample-status` dan source status: PASS.
- Lakehouse membaca `/api/lakehouse/summary`: PASS.
- Orkestrasi trigger endpoint pipeline: PASS.
- Analytics submit UAT dummy: PASS.
- Tombol Run Quality Gate berfungsi: PASS.
- Tombol Run Bronze berfungsi: PASS.
- Tombol Run Silver berfungsi: PASS.
- Tombol Run Gold berfungsi: PASS.
- Tombol Validate Gold berfungsi: PASS.
- Tombol Full Run Basic berfungsi: PASS.
- Loading state muncul: PASS.
- Success state muncul: PASS.
- Error state muncul jika command gagal: PASS.
- Empty state tersedia di kode UI untuk output yang belum ada: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-12-final-test.md`.
