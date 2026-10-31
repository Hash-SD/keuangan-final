# Superset Dashboard Spec — SILARAS SD

Dashboard: `SILARAS SD - Dashboard Anggaran IKU`  
Slug: `dashboard-anggaran-iku-prodi`

Dashboard baru memakai nama dasar tersebut dengan nomor urut numerik, misalnya
`SILARAS SD - Dashboard Anggaran IKU 1`, `... 2`, dan seterusnya. UUID
pipeline tidak boleh muncul pada nama dashboard, slug, atau nama chart.

Dashboard memakai model data Gold terdenormalisasi berbasis laporan tahunan. Tabel utama tetap:

```text
gold.fact_anggaran
```

Grain: satu item anggaran x satu alokasi IKU. Nilai Total Anggaran selalu memakai:

```text
SUM(jumlah_weighted_iku)
```

Filter dashboard resmi hanya:

- tahun
- prodi
- iku
- kegiatan
- akun

KPI resmi:

- Total Anggaran
- Jumlah Item
- Jumlah IKU
- Jumlah Kegiatan
- Status Rekonsiliasi

Status Rekonsiliasi berasal dari `gold.vw_dashboard_reconciliation` dan tidak diperlakukan sebagai nilai yang dijumlahkan.

## Registry chart

Registry runtime adalah sumber kebenaran dan harus menghasilkan 13 chart aktif:

1. `kpi_total_anggaran`
2. `kpi_jumlah_item`
3. `kpi_jumlah_iku`
4. `kpi_jumlah_kegiatan`
5. `kpi_status_rekonsiliasi`
6. `ringkasan_per_tahun`
7. `anggaran_per_tahun`
8. `anggaran_per_iku`
9. `cluster_kegiatan`
10. `komposisi_akun`
11. `anggaran_per_akun`
12. `detail_item_biaya`
13. `validasi_rekap`

Validasi deployment harus memenuhi `desired_chart_count == attached_chart_count == 13`. Chart lama yang dikelola registry boleh dilepaskan dari layout, tetapi chart milik pengguna tidak dihapus.

`Ringkasan per Tahun` adalah tabel ringkasan tanpa `Show Cell Bars`. Nominal
ditampilkan dengan format ribuan tanpa pecahan biner: `#,##0`. Nilai sumber
yang secara matematis memang pecahan akibat alokasi IKU tetap disimpan untuk
menjaga rekonsiliasi, tetapi tampilan Superset membulatkan visualnya ke Rupiah.

## Registry saved query analitik

Saved query di Superset dikelola lewat `SAVED_QUERY_REGISTRY` pada
`src/sql/setup_superset_excel_assets.py` dan menghasilkan 10 query `SILARAS - ...`.
Semua angka exact tanpa pembulatan dan mengikuti kontrak `GOLD_METRICS`:
`SUM(jumlah_weighted_iku)` untuk anggaran (bukan `SUM(jumlah)`), serta
`COUNT(DISTINCT item_id/kode_iku/kegiatan)` untuk hitungan.

| Label | Isi |
| --- | --- |
| `SILARAS - KPI Ringkasan Anggaran` | 1 baris KPI: total_anggaran, jumlah_item, jumlah_iku, jumlah_kegiatan |
| `SILARAS - KPI per Tahun` | KPI lengkap per tahun (mirror chart Ringkasan per Tahun) |
| `SILARAS - Anggaran per IKU` | tahun, iku, total_anggaran, jumlah_item |
| `SILARAS - Anggaran per Kegiatan` | tahun, cluster_kegiatan, kegiatan, total_anggaran, jumlah_item |
| `SILARAS - Anggaran per Akun` | tahun, akun, total_anggaran, jumlah_item |
| `SILARAS - Anggaran per Prodi` | KPI per prodi dan fakultas |
| `SILARAS - Rekonsiliasi per Sumber` | tahun, source_file, total_detail, total_rekap, selisih, status |
| `SILARAS - Detail Data Gold Lengkap` | seluruh kolom kontrak `FACT_COLUMNS` tanpa agregasi |
| `SILARAS - Detail Item Biaya (tanpa kolom teknis)` | detail faktual tanpa kolom teknis |
| `SILARAS - Cek Kolom Teknis (audit)` | kolom teknis masih ada di tabel Gold |

## Layout terkunci (dashboard layout snapshot)

Susunan visual dashboard (`position_json`) dikunci di `superset_assets/dashboard_layout.json`.
Snapshot menyimpan tiap node CHART dengan kunci `meta.registryKey` (bukan `chartId`),
sehingga layout tetap dipakai ulang walau chart ID berubah saat update atau
pembuatan instance dashboard baru. Chart registry yang belum ada di snapshot
otomatis ditambahkan sebagai baris baru di bawah grid.

- Script sinkronisasi memakai snapshot ini untuk `position_json`;
  susunan kurasi manual tidak ditimpa lagi.
- Untuk merekam ulang susunan terbaru setelah kurasi manual, jalankan
  script dengan `SUPERSET_CAPTURE_LAYOUT=1`.
- Lokasi snapshot dapat diarahkan dengan env `SUPERSET_LAYOUT_SNAPSHOT`.

## Label presentasi

Nama fisik dipertahankan untuk query dan lineage, sedangkan Superset menampilkan label bisnis:

| Nama fisik | Label tampilan |
| --- | --- |
| `source_file` | Sumber Data |
| `uraian_detail` | Detail |
| `harga_satuan` | Harga Satuan |
| `jumlah` | Jumlah Anggaran |
| `jumlah_weighted_iku` | Alokasi Anggaran IKU |
| `total_detail` | Detail Total |
| `total_rekap` | Total Rekap |
| `selisih` | Selisih |
| `status` | Status |
| `prodi` | Program Studi |
| `akun` | Akun Belanja |
| `kegiatan` | Kegiatan |
| `iku` | IKU |
| `tahun` | Tahun |

Kolom teknis `mapping_status`, `data_quality_flag`, `source_sheet`, dan `source_row` tetap tersedia untuk audit namun disembunyikan dari tampilan umum.

Script sinkronisasi:

```text
src/sql/setup_superset_excel_assets.py
```
