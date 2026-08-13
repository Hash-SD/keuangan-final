# Desain Refactor Gold Tahunan dan Dashboard RAB/IKU (One-Gold)

Tanggal: 2026-08-13
Status: draft revisi; menunggu persetujuan sebelum implementation plan

## 1. Tujuan

Refactor menyelaraskan pipeline Excel, Gold, PostgreSQL/Trino, Superset, portal lokal, test, dan dokumentasi dengan perubahan minimum yang aman.

Sistem menggunakan satu tabel Gold fisik:

```text
gold.fact_anggaran
```

Struktur dimensional hanya digunakan sebagai konsep analitik dan diagram penulisan. Tidak ada tabel dimensi fisik, bridge table, atau tabel agregasi baru.

## 2. Arsitektur dan grain

```text
Bronze/Silver
  ├── menyimpan periode sumber, hasil parsing, dan metadata lineage
  └── memilih serta menggabungkan sumber tahunan
             ↓
Gold: fact_anggaran
  └── 1 baris = 1 item anggaran × 1 alokasi IKU
             ↓
View dashboard (proyeksi, bukan tabel Gold baru)
  ├── Superset
  └── Portal lokal
```

`item_id` dapat muncul beberapa kali jika item memiliki beberapa IKU. Grain unik yang divalidasi adalah:

```text
(dataset_session_id, run_id, item_id, kode_iku)
```

Jika `item_id` bentrok antar sumber, pipeline membentuk identitas stabil yang menyertakan konteks sumber, bukan path absolut atau urutan eksekusi.

## 3. Keputusan arsitektur yang tetap

- `gold.fact_anggaran` adalah satu-satunya tabel Gold fisik.
- `tahun` adalah satu-satunya atribut waktu analitik.
- `periode` tidak boleh ada pada fact, view analitik, dataset Superset, filter, metric, API dashboard, atau fixture dashboard.
- Informasi `Jan-Jun`, `Jul-Des`, dan sumber tahunan hanya berada di Bronze/Silver atau metadata lineage/audit.
- `dataset_session_id` dan `run_id` menjadi identitas data.
- `pipeline_run_id` dan `airflow_dag_run_id` hanya berada pada manifest/audit dan tidak menjadi kolom fact.
- `allocation_weight` dan `jumlah_weighted_iku` dipertahankan karena grain fact adalah item × IKU.
- Total nominal dashboard selalu memakai `SUM(jumlah_weighted_iku)`.
- `Status Rekonsiliasi` adalah status validasi dari quality gate/manifest, bukan metric penjumlahan.
- Tidak ada referensi produktif ke `nominal_piutang_rp`, `tahun_akademik`, `nama_debitur`, `vw_dashboard_piutang_ukt`, `nim`, atau istilah kualitas piutang.

## 4. Kontrak Gold minimal

Kontrak berada di `src/gold/contract.py` dan menjadi sumber kebenaran untuk urutan kolom, tipe, grain, metric, filter, dan validasi.

### 4.1 Kolom identitas, analitik, dan nominal

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
```

### 4.2 Kolom lineage dan quality minimum

```text
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

Kolom audit tetap berada pada satu fact agar quality gate dan lineage tidak kehilangan bukti, tetapi seluruhnya disembunyikan dari view Superset. `nama_akun_asli` dipertahankan di Silver sebagai nilai sumber; Gold memakai nama akun kanonik. Kolom `pipeline_run_id` dan `airflow_dag_run_id` tidak masuk fact.

### 4.3 Tipe lintas layer

- atribut dan lineage: `TEXT`;
- `tahun`: `TEXT`, wajib cocok dengan pola `20XX` agar kompatibel dengan CSV/parser saat ini;
- `qty`, `harga_satuan`, `jumlah`, `allocation_weight`, `jumlah_weighted_iku`: `DOUBLE PRECISION`;
- `source_row`: `INTEGER`;
- `created_at`: `TIMESTAMPTZ` UTC.

## 5. Aturan nominal IKU

`jumlah` adalah nominal item sumber dan boleh berulang pada beberapa baris IKU. `jumlah_weighted_iku` adalah nominal analitik yang aditif:

```text
allocation_weight = 1 / jumlah IKU pada item
jumlah_weighted_iku = jumlah × allocation_weight
```

Invariant wajib:

```text
SUM(allocation_weight) = 1 per (dataset_session_id, run_id, item_id)
jumlah_weighted_iku = jumlah × allocation_weight
SUM(jumlah_weighted_iku) = total nominal sumber
```

Tidak ada agregasi yang disimpan sebagai tabel Gold. Agregasi dilakukan oleh query Superset atau view dashboard.

## 6. View dashboard

View dashboard adalah proyeksi dari `gold.fact_anggaran`, bukan Gold fisik kedua. Kolom yang diekspos:

```text
tahun
item_id
source_file
prodi
fakultas
iku
kode_iku
kegiatan
cluster_kegiatan
akun
uraian_detail
qty
satuan
harga_satuan
jumlah
```

Pada view:

```sql
jumlah_weighted_iku AS jumlah
```

Kolom teknis tidak ditampilkan pada dataset Superset, tetapi tetap tersedia di fact untuk quality gate dan audit.

Filter Superset:

```text
tahun, prodi, iku, kegiatan, akun
```

## 7. KPI dan registry chart

KPI final:

```text
Total Anggaran      = SUM(jumlah_weighted_iku)
Jumlah Item         = COUNT(DISTINCT item_id)
Jumlah IKU          = COUNT(DISTINCT kode_iku)
Jumlah Kegiatan     = COUNT(DISTINCT kegiatan)
Status Rekonsiliasi = status quality gate/manifest
```

Status Rekonsiliasi ditampilkan sebagai status card/label dari manifest atau endpoint quality gate. Status tersebut tidak dipaksa menjadi angka pada query fact dan tidak dihitung dengan `SUM`.

Registry dashboard berisi tepat 13 chart stabil. Definisi dataset, runtime Superset, snapshot, dan test harus memiliki nama chart, metric, filter, serta jumlah chart yang sama. KPI `Total Weighted IKU` sebagai KPI terpisah dihapus karena identik dengan `Total Anggaran`.

## 8. Penggabungan laporan tahunan

1. Setiap sumber harus memiliki tahun anggaran yang konsisten.
2. Satu workbook tahunan digunakan setelah validasi.
3. Workbook parsial pada tahun yang sama digabung hanya jika sumber tidak tumpang tindih.
4. Workbook tahunan dan parsial dibandingkan berdasarkan identitas sumber, cakupan, dan total rekonsiliasi.
5. Jika overlap tidak terbukti aman, pipeline berhenti dengan `AMBIGUOUS_SOURCE_OVERLAP`.
6. Deduplicasi tidak boleh hanya memakai nama kegiatan, akun, atau uraian.
7. `source_file`, `source_sheet`, `source_row`, dan `item_id` menjadi bukti lineage.
8. Data 2023 Jan-Jun dan Jul-Des menjadi satu laporan tahunan jika tidak overlap.
9. Metadata seleksi mencatat sumber terpilih, sumber yang dikeluarkan, periode sumber, status overlap, total sumber, dan total Gold.

## 9. Quality gate

`src/validation/production_quality_gate.py` memvalidasi:

- schema fact sama dengan kontrak;
- tidak ada `periode` atau domain piutang pada Gold dan artefak analitik;
- setiap baris memiliki `dataset_session_id`, `run_id`, tahun, dan lineage minimum;
- `allocation_weight` berada pada `[0, 1]`;
- jumlah bobot per item sama dengan `1`;
- formula weighted benar;
- grain `(dataset_session_id, run_id, item_id, kode_iku)` tidak duplikat;
- total weighted cocok dengan total sumber;
- dataset Superset hanya mengekspos kolom dashboard;
- lima KPI dan lima filter sesuai kontrak;
- status rekonsiliasi tersedia dari quality gate/manifest.

## 10. Urutan perubahan

```text
contract.py
  → fact_anggaran.py
  → seleksi dan merge tahunan pada pipeline
  → quality gate
  → DDL/loader satu fact
  → view dashboard
  → Superset dan portal lokal
  → test kontrak, smoke test, dan dokumentasi
```

Setiap fase harus lulus test sebelum fase berikutnya dimulai. Tidak ada perubahan ke physical dimension table pada refactor ini.

## 11. Bahasa penulisan

Untuk skripsi, struktur dimensional boleh ditampilkan sebagai logical star schema. Implementasi harus dijelaskan sebagai:

> Gold merupakan satu tabel fakta terdenormalisasi `gold.fact_anggaran` dengan struktur dimensional secara logis. Dimensi pada diagram merepresentasikan kelompok atribut analitik, bukan tabel dimensi fisik yang terpisah.
