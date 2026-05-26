# Context7 Notes: Docker Compose

Sumber Context7: `/docker/compose`.

- Gunakan network bernama agar service dapat saling resolve memakai nama service.
- Gunakan named volume untuk stateful service seperti MinIO, PostgreSQL metastore, Airflow, dan Superset.
- Healthcheck mendukung `test`, `interval`, `timeout`, `start_period`, dan `retries`.
- `depends_on` berguna untuk mengatur urutan startup, terutama bila dikombinasikan dengan kondisi service sehat.
- Compose mengamati health status, tetapi tidak otomatis memperbaiki container unhealthy tanpa restart policy.
- Environment variable dapat didefinisikan sebagai mapping YAML dan diambil dari `.env`.

Implikasi proyek:

- Semua service masuk network `lakehouse_net`.
- Gunakan healthcheck untuk MinIO, PostgreSQL, Airflow, Trino, dan Superset.
- Hindari konfigurasi port implisit; setiap UI diberi port host yang jelas sesuai plan.

