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
