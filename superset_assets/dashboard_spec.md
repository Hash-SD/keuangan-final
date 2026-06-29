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
- mapping_status
- data_quality_flag

Chart minimal:

- KPI Total Anggaran
- KPI Total Anggaran Weighted IKU
- KPI Jumlah IKU
- KPI Jumlah Kegiatan
- KPI Jumlah Item
- KPI Mapping OK %
- Bar Chart Anggaran per IKU
- Treemap IKU -> Cluster Kegiatan
- Bar Chart Anggaran per Akun
- Table Detail Item
- Table Mapping Quality
- Table Validation/Reconciliation

Script otomatis:

```text
src/sql/setup_superset_excel_assets.py
```
