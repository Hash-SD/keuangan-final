# Context7 Notes: Apache Superset

Sumber Context7: `/apache/superset`.

- Setup awal menjalankan `superset db upgrade` dan membuat admin user.
- Database connection dapat dibuat manual lewat UI atau API `/api/v1/database/`.
- Dataset dibuat dari database, schema, dan table atau view.
- Chart dan dashboard dapat dikelola lewat API, tetapi fallback manual tetap valid untuk local stack.

Implikasi proyek:

- Superset akan memakai koneksi SQLAlchemy Trino.
- Dataset utama adalah view `gold.vw_dashboard_piutang_ukt`.
- Dashboard minimal memuat Big Number, bar chart, pie/gauge, time-series, table, dan native filters.

