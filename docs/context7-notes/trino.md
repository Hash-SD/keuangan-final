# Context7 Notes: Trino

Sumber Context7: `/trinodb/trino`.

- Iceberg connector menggunakan catalog properties, misalnya `connector.name=iceberg`.
- Catalog dapat memakai JDBC metastore atau REST catalog.
- Trino menyediakan metadata table seperti `system.iceberg_tables` dan `$properties` untuk inspeksi.

Implikasi proyek:

- File catalog target ada di `config/trino/catalog/iceberg.properties`.
- Query validasi Gold ditempatkan di `src/sql/trino_validation_queries.sql`.
- Koneksi Superset diarahkan ke Trino setelah catalog Gold tersedia.

