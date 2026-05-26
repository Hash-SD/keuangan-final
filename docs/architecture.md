# Architecture

Sistem memakai Medallion Architecture:

- Bronze: data mentah PDF/CSV/Excel disimpan dengan metadata lineage.
- Silver: data dibersihkan, tipe distandarkan, dan data invalid dipisahkan ke quarantine.
- Gold: star schema untuk analisis piutang UKT Prodi Sains Data.

Komponen target:

- MinIO sebagai object storage S3-compatible.
- Spark untuk transformasi Bronze, Silver, dan Gold.
- Iceberg sebagai format tabel lakehouse.
- Trino untuk query SQL atas Gold layer.
- Superset untuk dashboard.
- Airflow untuk orkestrasi DAG end-to-end.

