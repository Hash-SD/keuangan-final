# Desain Refactor Gold Tahunan dan Dashboard RAB/IKU

Tanggal: 2026-08-13
Status: disetujui secara percakapan; menunggu review spec sebelum implementation plan

## Tujuan

Refactor dilakukan bertahap untuk menyelaraskan pipeline, Gold, PostgreSQL, Trino, Superset, portal lokal, test, dan dokumentasi tanpa mengubah seluruh sistem sekaligus.

Sistem mempertahankan satu tabel Gold utama:

```text
gold.fact_anggaran
```

Modelnya adalah model data Gold terdenormalisasi berbasis laporan tahunan dengan struktur dimensional secara logis. Tidak ada tabel dimensi fisik yang ditambahkan.

Grain kanonik:

```text
1 baris = 1 item anggaran × 1 alokasi IKU
```

## Keputusan yang tidak boleh berubah

- `fact_anggaran` adalah satu-satunya tabel Gold utama.
- `tahun` adalah satu-satunya atribut waktu analitik di Gold, Superset, portal, dan dashboard.
- `periode` tidak boleh ada di `fact_anggaran`, dataset Superset, filter, metric, view analitik, atau KPI.
- Informasi Jan-Jun, Jul-Des, dan sumber tahunan hanya disimpan di Bronze/Silver atau metadata lineage/audit.
- `dataset_session_id` dan `run_id` adalah identitas data utama.
- `pipeline_run_id` tetap boleh berada pada manifest/audit pipeline, tetapi tidak menjadi kolom Gold duplikat ketika nilainya sama dengan `run_id`.
- Metric nominal utama adalah `SUM(jumlah_weighted_iku)`.
- `Status Rekonsiliasi` adalah status validasi, bukan metric penjumlahan.
- KPI final: `Total Anggaran`, `Jumlah Item`, `Jumlah IKU`, `Jumlah Kegiatan`, dan `Status Rekonsiliasi`.
- Referensi produktif domain piutang berikut harus hilang: `nominal_piutang_rp`, `tahun_akademik`, `nama_debitur`, `vw_dashboard_piutang_ukt`, `nim`, dan istilah kualitas piutang.

## Kontrak Gold kanonik

Kontrak didefinisikan di `src/gold/contract.py` dan menjadi sumber kebenaran untuk urutan kolom, tipe, grain, metric, filter, dan validasi. Artefak SQL/JSON tetap dapat dibaca manusia, tetapi test harus memastikan isinya sama dengan kontrak.

Urutan kolom Gold:

```text
item_id
dataset_session_id
run_id
tahun
prodi
fakultas
kegiatan
cluster_kegiatan
akun
kode_akun
nama_akun
nama_akun_asli
iku
kode_iku
nama_iku
nomenklatur_path
uraian_detail
qty
satuan
harga_satuan
jumlah
allocation_weight
jumlah_weighted_iku
mapping_status
data_quality_flag
source_file
source_sheet
source_row
source_role
row_type
quality_flags
created_at
```

Kontrak tidak memasukkan `periode`, `pipeline_run_id`, atau `airflow_dag_run_id`.

Tipe lintas layer:

- atribut teks dan lineage: `TEXT`;
- `tahun`: `TEXT` yang wajib tervalidasi sebagai tahun anggaran empat digit agar kompatibel dengan CSV/parser yang ada;
- `qty`, `harga_satuan`, `jumlah`, `allocation_weight`, dan `jumlah_weighted_iku`: `DOUBLE PRECISION`;
- `source_row`: `INTEGER`;
- `created_at`: `TIMESTAMPTZ`, direpresentasikan sebagai waktu UTC pada DataFrame/Parquet.

Metric kanonik:

```text
Total Anggaran    = SUM(jumlah_weighted_iku)
Jumlah Item       = COUNT(DISTINCT item_id)
Jumlah IKU        = COUNT(DISTINCT kode_iku)
Jumlah Kegiatan   = COUNT(DISTINCT kegiatan)
Status Rekonsiliasi = status validasi Gold/manifest, bukan SUM
```

`jumlah` tetap dipertahankan sebagai nominal item sumber, tetapi tidak boleh dipakai sebagai total agregat dashboard pada allocation-grain.

## Penggabungan laporan tahunan

Penggabungan dilakukan sebelum pembentukan Gold dan tidak mengandalkan `periode` sebagai kolom Gold.

1. Setiap sumber harus memiliki tahun anggaran yang dapat ditentukan dari metadata/sumber dan harus konsisten dengan barisnya.
2. Satu workbook untuk satu tahun dipakai langsung setelah validasi.
3. Beberapa workbook parsial dalam satu tahun digabungkan jika identitas sumbernya tidak tumpang tindih.
4. Jika terdapat workbook tahunan dan parsial pada tahun yang sama, pipeline membandingkan cakupan dan rekonsiliasi. Workbook tahunan hanya dipilih bila seluruh data parsial terbukti tercakup dan totalnya cocok.
5. Jika cakupan tidak dapat dibuktikan, pipeline berhenti dengan status `AMBIGUOUS_SOURCE_OVERLAP` dan melaporkan file/sheet/baris yang bertabrakan.
6. Deduplicasi tidak boleh menggunakan nama kegiatan, akun, atau `uraian_detail` saja.
7. Identitas sumber minimal adalah `dataset_session_id`, `item_id`, `source_file`, `source_sheet`, dan `source_row`.
8. Jika `item_id` bertabrakan antarfile, pembentukannya diperbaiki agar memiliki konteks sumber yang stabil. Kunci turunan tidak boleh bergantung pada path absolut atau urutan eksekusi.
9. Workbook Jan-Jun dan Jul-Des tahun 2023 menjadi satu laporan tahunan jika tidak overlap.
10. Metadata hasil seleksi menyimpan tahun, sumber terpilih, sumber yang dikeluarkan, informasi periode sumber, status overlap, total sumber, dan total Gold.

Informasi periode boleh tetap berada di Silver untuk audit dan keputusan overlap. Informasi tersebut tidak boleh dipropagasikan ke fact, view analitik, dataset Superset, API dashboard, atau fixture dashboard.

## Quality gate

`src/validation/production_quality_gate.py` memvalidasi:

- urutan dan kelengkapan schema Gold terhadap kontrak;
- semua baris memiliki `dataset_session_id`, `run_id`, tahun, dan lineage wajib;
- `periode` tidak ada pada kolom Gold maupun artefak analitik;
- kolom domain piutang tidak ada pada Gold, portal, Superset, dan test produktif;
- `allocation_weight` berada pada rentang `[0, 1]`;
- untuk setiap `(dataset_session_id, run_id, item_id)`, jumlah `allocation_weight` adalah `1` dengan toleransi numerik;
- `jumlah_weighted_iku == jumlah * allocation_weight`;
- grain `(item_id, kode_iku)` tidak duplikat dalam dataset/run;
- tidak ada item hasil overlap yang terduplikasi;
- semua sumber memiliki tahun dan status penggabungan/rekonsiliasi tahunan valid;
- total Gold sama dengan total sumber yang dipilih setelah weighting.

Status `AMBIGUOUS_SOURCE_OVERLAP` bersifat blocking: pipeline tidak boleh menulis pointer Gold `PUBLISHED`.

## SQL, loader, dan lintas engine

`create_gold_tables.sql`, `load_gold_to_postgres.py`, output CSV/Parquet, dan view dashboard dibangun dari kontrak yang sama.

View yang tetap diperbolehkan adalah view dashboard/reconciliation, bukan tabel Gold tambahan. View tidak boleh memperkenalkan `periode` sebagai atribut analitik. View reconciliation dapat menyediakan status tekstual untuk KPI `Status Rekonsiliasi`.

PostgreSQL dan Trino wajib dibandingkan berdasarkan `dataset_session_id` dan `run_id` yang sama, dengan pemeriksaan:

- jumlah baris;
- jumlah item unik;
- total weighted;
- status rekonsiliasi.

## Portal lokal

Portal membaca `fact_anggaran` melalui Superset API dan fallback CSV/Parquet Gold yang sama. Filter dashboard lokal hanya:

```text
tahun, prodi, iku, kegiatan, akun
```

Summary portal menggunakan lima KPI kanonik. Detail menampilkan atribut RAB/IKU dan menggunakan `jumlah_weighted_iku` sebagai nilai alokasi yang aman untuk agregasi. Tidak ada adapter produktif, label, fallback, fixture, atau selector yang memakai domain piutang.

## Superset dan registry chart

Registry chart stabil menjadi sumber kebenaran nama, key, metric, groupby, layout, dan jumlah chart. Registry wajib memiliki tepat 13 key:

```text
kpi_total_anggaran
kpi_jumlah_item
kpi_jumlah_iku
kpi_jumlah_kegiatan
kpi_status_rekonsiliasi
ringkasan_per_tahun
anggaran_per_tahun
anggaran_per_iku
cluster_kegiatan
komposisi_akun
anggaran_per_akun
detail_item_biaya
validasi_rekap
```

Registry menghasilkan `charts_definition.json` dan dipakai script setup Superset. Chart yang dikelola sistem diberi identitas/key stabil. Saat sinkronisasi:

- chart dikelola di-upsert berdasarkan key stabil;
- ID Superset disimpan pada manifest/report;
- chart lama yang dikelola sistem tetapi tidak ada di registry dilepas dari layout;
- chart pengguna yang tidak memiliki identitas managed tidak dihapus;
- hasil valid hanya jika `desired_chart_count == attached_chart_count == 13`.

Native filter Superset hanya `tahun`, `prodi`, `iku`, `kegiatan`, dan `akun`. Tidak ada filter `periode`.

## Urutan implementasi

### Fase 0 — Baseline

Catat status git, compileall, seluruh pytest, serta kegagalan awal. Kegagalan baseline tidak boleh disamarkan sebagai regresi.

### Fase 1 — Kontrak kanonik

Buat kontrak, test schema/tipe/grain/metric, dan selaraskan definisi dataset/SQL/loader tanpa menyentuh UI lebih dulu.

### Fase 2 — Fact dan pipeline

Gunakan kontrak pada pembentukan fact, tambahkan identitas dataset/run secara immutable, keluarkan `periode` dari Gold, dan implementasikan pemilihan/penggabungan sumber tahunan beserta status overlap.

### Fase 3 — Quality gate

Perketat schema, tahun, weighting, uniqueness, sumber, rekonsiliasi, larangan periode, dan larangan domain piutang.

### Fase 4 — SQL dan loader

Selaraskan DDL, view, loader, CSV/Parquet, PostgreSQL, dan Trino.

### Fase 5 — Portal lokal

Migrasikan backend, frontend, fixture, dan Playwright dari kontrak piutang ke kontrak anggaran tahunan.

### Fase 6 — Superset

Tambahkan registry 13 chart, lima KPI, lima filter, managed-chart detach, dan artefak JSON/Markdown yang dihasilkan dari registry.

### Fase 7 — Dokumentasi dan test

Perbarui README, `docs/architecture.md`, AI codebase guide, Superset assets, seluruh fixture, dan test. Tambahkan kasus annual/partial/overlap, weighted allocation, no-period, no-legacy, filter, chart count, dan cross-engine.

Setelah setiap fase:

```bash
python -m compileall src dags portal_backend
python -m pytest tests -q
```

Setelah semua fase dan hanya jika layanan tersedia:

```bash
python scripts/run_release_fixture_smoke.py
python src/validation/runtime_cross_engine.py
python src/sql/setup_superset_excel_assets.py
npx playwright test tests/playwright/local-dashboard.spec.ts
npx playwright test tests/playwright/superset-dashboard.spec.ts
```

## Batasan dan non-goals

- Tidak membuat `dim_waktu`, `dim_prodi`, `dim_kegiatan`, `dim_akun`, atau `dim_iku` fisik.
- Tidak menghapus data produksi atau tabel produksi.
- Tidak memilih workbook yang overlap secara diam-diam.
- Tidak menghapus test hanya untuk membuat suite hijau.
- Tidak menjadikan `SUM(jumlah)` sebagai total dashboard.
- Tidak menyatakan selesai sebelum seluruh kontrak dan verifikasi yang tersedia lulus.
