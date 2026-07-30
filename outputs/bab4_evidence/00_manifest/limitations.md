# Limitations

- Audit menggunakan artefak lokal yang tersedia pada saat pemeriksaan.
- Workbook sumber tidak diubah; formula diprofilkan tetapi tidak dihitung ulang oleh audit.
- Laporan historis di outputs/reports tidak dianggap sebagai hasil baru tanpa pemeriksaan file sumber.
- UAT memerlukan instrumen dan respons pengguna; audit tidak membuat respons sintetis.
- Status Docker/Airflow/Trino/Superset hanya dianggap bukti runtime jika pemeriksaan service dilakukan dan dicatat.
