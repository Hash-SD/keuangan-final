# Context7 Notes: Apache Airflow

Sumber Context7: `/apache/airflow`.

- DAG didefinisikan sebagai kode Python, task dapat memakai TaskFlow API atau operator.
- Dependency dapat dibuat dengan pemanggilan task function atau operator `>>`.
- Untuk local Docker, pola umum adalah menyediakan folder `dags`, `logs`, dan `plugins`, menjalankan init database, lalu menjalankan webserver dan scheduler.
- `catchup=False` cocok untuk pipeline batch simulasi agar tidak menjalankan interval historis.

Implikasi proyek:

- DAG utama bernama `keuangan_prodi_lakehouse_dag`.
- Task dibuat linear sesuai plan: generate, quality gate, bronze, silver, gold, validation, metrics, refresh dataset.
- Log task perlu cukup jelas agar checkpoint dan audit mudah dilacak.

