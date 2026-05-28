# CHECKPOINT-E2E-08 - Superset

Tanggal: 2026-05-28
Status: PASS

## Perintah

```powershell
python src\sql\setup_superset_assets.py
python src\sql\setup_superset_dashboard.py
Invoke-WebRequest -Uri "http://localhost:8089/health" -UseBasicParsing
```

## Setup Assets

`setup_superset_assets.py` berhasil:

```json
{
  "database_id": 2,
  "dataset_id": 1,
  "database_name": "Trino Iceberg Gold Keuangan",
  "table_name": "vw_dashboard_piutang_ukt"
}
```

Artefak:

```text
outputs/reports/superset_assets.json
```

## Setup Dashboard

`setup_superset_dashboard.py` berhasil:

```json
{
  "dashboard_id": 1,
  "dashboard_title": "Dashboard Piutang UKT Prodi",
  "dashboard_url": "http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/",
  "chart_ids": [1, 2, 3, 4, 5, 6]
}
```

Artefak:

```text
outputs/reports/superset_dashboard.json
```

## Health Check

Superset health:

```text
HTTP 200 OK
```

URL dashboard:

```text
http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/
```

Credential default:

```text
admin / admin
```

## Acceptance

- Superset health OK: PASS.
- Database connection tercatat: PASS, `Trino Iceberg Gold Keuangan`.
- Dataset Gold tercatat: PASS, `vw_dashboard_piutang_ukt`.
- Dashboard tercatat: PASS, `Dashboard Piutang UKT Prodi`.
- Chart dashboard dibuat: PASS, 6 chart.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-09-portal-frontend.md`.
