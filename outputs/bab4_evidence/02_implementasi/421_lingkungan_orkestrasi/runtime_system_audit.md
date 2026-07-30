# Runtime system audit

Generated: `2026-07-30T10:23:25.260799+00:00`

| Check | Status | Evidence |
|---|---|---|
| `docker_compose_ps` | `VERIFIED` | exit_code=0 |
| `airflow_dags` | `VERIFIED` | exit_code=0 |
| `airflow_tasks` | `VERIFIED` | exit_code=0 |
| `airflow_runs` | `VERIFIED` | exit_code=0 |
| `successful_run_task_states` | `VERIFIED` | exit_code=0 |
| `postgres_version` | `VERIFIED` | exit_code=0 |
| `postgres_tables` | `VERIFIED` | exit_code=0 |
| `trino_info` | `VERIFIED` | HTTP 200 http://localhost:8082/v1/info |
| `airflow_health` | `VERIFIED` | HTTP 200 http://localhost:8085/health |
| `minio_health` | `VERIFIED` | HTTP 200 http://localhost:9000/minio/health/live |
| `superset_health` | `VERIFIED` | HTTP 200 http://localhost:8089/health |
| `portal_datasets` | `VERIFIED` | HTTP 200 http://localhost:8091/api/datasets |
| `portal_status` | `VERIFIED` | HTTP 200 http://localhost:8091/api/excel-lakehouse/status |
| `portal_dashboard_status` | `VERIFIED` | HTTP 200 http://localhost:8091/api/local-dashboard/status |
| `portal_frontend` | `VERIFIED` | HTTP 200 http://localhost:8090 |
