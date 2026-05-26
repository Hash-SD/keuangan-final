# Context7 Notes: MinIO

Sumber Context7: `/minio/minio-py`.

- Client Python dibuat dengan endpoint, access key, secret key, dan optional region.
- Bucket dicek dengan `bucket_exists`; jika belum ada dibuat dengan `make_bucket`.
- File lokal diunggah ke object storage dengan `fput_object`.
- MinIO Python client cocok untuk S3-compatible storage lokal.

Implikasi proyek:

- Bucket default `lakehouse` dibuat otomatis oleh helper.
- Bronze path memakai prefix seperti `bronze/pdf`, `bronze/csv`, dan `bronze/excel`.
- Metadata lineage tetap disimpan bersama data hasil ingest.

