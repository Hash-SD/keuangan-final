# Context7 Notes: Apache Spark

Sumber Context7: `/apache/spark`.

- PySpark membaca CSV dengan `spark.read.load(..., format="csv", header="true", inferSchema="true")`.
- Parquet direkomendasikan untuk storage analitik lokal karena columnar dan efisien.
- Spark DataFrame dapat ditulis dengan mode `overwrite` untuk pipeline deterministik.
- Konfigurasi seperti `spark.sql.shuffle.partitions` harus eksplisit agar hasil lokal lebih stabil.

Implikasi proyek:

- Transformasi awal dapat menghasilkan Parquet sebelum integrasi penuh Iceberg.
- Job Spark harus menerima path input/output dari config agar mudah dipakai Airflow.
- Untuk data kecil dummy, shuffle partition dibuat rendah.

