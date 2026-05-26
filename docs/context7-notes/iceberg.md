# Context7 Notes: Apache Iceberg

Sumber Context7: `/apache/iceberg`.

- Spark perlu extension `org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions`.
- Catalog Spark dapat memakai Hadoop catalog untuk lokal atau JDBC catalog untuk metastore.
- Warehouse path harus eksplisit dan dapat diarahkan ke filesystem lokal atau S3-compatible storage.
- Table dibuat dengan `USING iceberg`.

Implikasi proyek:

- Untuk stack Docker, gunakan warehouse S3-compatible MinIO.
- Untuk fallback lokal, hasil Gold dapat dibuat sebagai Parquet agar test tetap berjalan.
- Konfigurasi Iceberg akan ditempatkan di `config/spark/spark-defaults.conf`.

