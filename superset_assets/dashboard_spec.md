# Superset Dashboard Spec - SILARAS SD

Dashboard: `SILARAS SD - Dashboard Anggaran IKU`

Slug: `dashboard-anggaran-iku-prodi`

Dataset utama:

```text
gold.fact_anggaran
```

Filter wajib:

- tahun
- periode
- prodi
- iku
- kegiatan
- akun

Kolom tersembunyi (tetap ada di tabel gold, tidak ditampilkan di Superset):

- mapping_status
- data_quality_flag
- source_sheet
- source_row

Label tampilan Superset:

Nama kolom fisik tetap dipakai untuk query dan lineage, sedangkan Superset menampilkan label bisnis berikut:

| Kolom fisik | Label tampilan |
| --- | --- |
| `source_file` | Sumber Data |
| `uraian_detail` | Detail |
| `harga_satuan` | Harga Satuan |
| `jumlah` | Jumlah Anggaran |
| `jumlah_weighted_iku` | Alokasi Anggaran IKU |
| `prodi` | Program Studi |
| `akun` | Akun Belanja |
| `kegiatan` | Kegiatan |
| `iku` | IKU |
| `tahun` | Tahun |

Dataset ditampilkan sebagai **Data Anggaran RAB/IKU**, tetapi tabel fisiknya tetap `gold.fact_anggaran`.

Chart minimal:

- KPI Total Anggaran
- KPI Total Anggaran Weighted IKU
- KPI Jumlah IKU
- KPI Jumlah Kegiatan
- KPI Jumlah Item
- Bar Chart Anggaran per IKU
- Treemap IKU -> Cluster Kegiatan
- Bar Chart Anggaran per Akun
- Table Detail Item (tanpa kolom teknis)
- Table Validation/Reconciliation

Saved queries (dibuat otomatis oleh script):

- `SILARAS - Detail Item Biaya (tanpa kolom teknis)` — cek data gold tanpa atribut teknis
- `SILARAS - Cek Kolom Teknis (audit)` — pastikan kolom teknis masih eksis di tabel

Script otomatis:

```text
src/sql/setup_superset_excel_assets.py
```
