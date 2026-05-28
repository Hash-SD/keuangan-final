# CHECKPOINT-AUDIT-03: Init Container Audit

Tanggal: 2026-05-28
Status: Selesai

## Command

```powershell
docker inspect keuangan-airflow-init --format "{{.State.Status}} {{.State.ExitCode}}"
docker inspect keuangan-minio-init --format "{{.State.Status}} {{.State.ExitCode}}"
docker logs keuangan-airflow-init --tail=100
docker logs keuangan-minio-init --tail=100
```

## Exit Code

```text
keuangan-airflow-init: exited 0
keuangan-minio-init: exited 0
```

## Airflow Init Log

Ringkasan log:

```text
Performing upgrade to the metadata database postgresql+psycopg2://lakehouse:***@postgres-metastore:5432/metastore
Context impl PostgresqlImpl.
Will assume transactional DDL.
Creating tables
Database migrating done!
airflow already exist in the db
```

Catatan nonfatal:

```text
Using the in-memory storage for tracking rate limits as no storage was explicitly specified.
```

Ini warning umum untuk mode lokal/development Airflow web UI, bukan kegagalan init.

## MinIO Init Log

Ringkasan log:

```text
Added `local` successfully.
Bucket created successfully `local/lakehouse`.
Access permission for `local/lakehouse` is set to `private`
```

## Keputusan Audit

- `keuangan-airflow-init` adalah init-only container. Status `exited` dengan exit code `0` adalah OK.
- `keuangan-minio-init` adalah init-only container. Status `exited` dengan exit code `0` adalah OK.
- Tidak perlu restart init container terus-menerus.

## Acceptance

- `airflow-init` dinyatakan OK jika exit 0: PASS.
- `minio-init` dinyatakan OK jika exit 0: PASS.
- Log penyebab/status dicatat: PASS.
- Tidak ada error init blocking: PASS.
