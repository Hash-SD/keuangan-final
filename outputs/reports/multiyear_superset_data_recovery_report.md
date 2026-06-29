# Multiyear Superset Data Recovery Report

Generated at: 2026-06-29

## Status

PASS for local Gold, PostgreSQL, Trino, and Superset asset regeneration.

## Root Cause

Superset previously showed only 2025 because the default pipeline discovery could fall back to a 2025 workbook when the active dataset pointer referenced 2023 files that no longer existed. The pipeline could parse 2023 and 2024, but normal discovery was not guaranteed to select the complete uploaded bundle.

## Fixes Applied

- `discover_excel_sources()` now prefers a complete uploaded Excel bundle containing:
  - `RAB 2025 SD RAB IKU.xlsx`
  - `Nomenklatur.xlsx`
  - `Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx`
  - `RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx`
  - `RAB_SD_Usulan KE (1)_jul-des 2023.xlsx`
- Year and period metadata are inferred per file name, so 2023, 2024, and 2025 are not overwritten by stale global pointer metadata.
- Test and dummy raw folders are excluded from automatic discovery.
- Existing uploaded raw files are reused as archive evidence instead of creating duplicate workbook copies on every run.
- `fact_anggaran` excludes Silver candidate rows with missing `jumlah`, so Gold contains only final budget rows with financial values.

## Latest Pipeline Evidence

- Pipeline evidence: `outputs/evidence/latest_multiyear_pipeline_output.txt`
- PostgreSQL load evidence: `outputs/evidence/latest_postgres_load_output.txt`
- Superset setup evidence: `outputs/evidence/latest_superset_setup_output.txt`
- PostgreSQL multiyear counts: `outputs/evidence/latest_postgres_multiyear_counts.txt`
- Local validation JSON: `outputs/evidence/multiyear_gold_validation.json`

## Latest Counts

| Layer | Count |
| --- | ---: |
| Bronze cells | 55,340 |
| Silver RAB items | 445 |
| Nomenklatur detail | 248 |
| Gold fact_anggaran rows | 502 |

## Gold Rows by Year

| Tahun | Rows | Total jumlah | Total weighted IKU |
| --- | ---: | ---: | ---: |
| 2023 | 62 | 121,405,000 | 121,405,000 |
| 2024 | 79 | 94,675,950 | 94,675,950 |
| 2025 | 361 | 1,279,879,331 | 935,795,331 |

## Dashboard State

Superset API returned `validated` after regeneration:

- Dataset: `gold.fact_anggaran`
- Dashboard: `SILARAS SD - Dashboard Anggaran IKU`
- Chart count: 12
- URL: `http://localhost:8089/superset/dashboard/dashboard-anggaran-iku-prodi/`

## Notes

No financial values were edited manually. The change removes non-financial candidate rows from Gold and keeps review labels for rows whose IKU or account cannot be proven confidently from workbook content plus nomenklatur.
