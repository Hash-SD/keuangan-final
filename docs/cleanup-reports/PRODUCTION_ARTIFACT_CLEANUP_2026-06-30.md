# Production Artifact Cleanup - 2026-06-30

## Summary

Removed runtime artifacts from Git tracking so `feature/excel-lakehouse-v2-final` can be merged toward production with source code, configuration, DAGs, portal code, and tests only.

## Removed From Git Tracking

- `data/generated/**`
- `data/raw/excel_lakehouse/**/*.xlsx`
- `data/tmp/**`
- `outputs/reports/**`
- `outputs/metrics/**`
- `outputs/evidence/**`
- `outputs/logs/**`
- `outputs/screenshots/**`
- `.jules/**`
- `FINAL_VERIFICATION_REPORT.md`
- `docs/brainstorming/pipeline_count_validation.md`

Files were removed from the Git index with `git rm --cached`, so local runtime files can remain on the development machine but will not be part of the production branch.

## Preserved Runtime Structure

Tracked `.gitkeep` placeholders were added for:

- `data/generated/`
- `data/raw/excel_lakehouse/`
- `data/uploads/staging/`
- `outputs/reports/`
- `outputs/metrics/`
- `outputs/evidence/`
- `outputs/logs/`
- `outputs/screenshots/`

## Test Adjustment

`tests/test_rab_parser_amount_columns.py` now creates minimal `.xlsx` workbooks in `tmp_path` instead of depending on raw uploaded Excel files. This preserves parser regression coverage without committing sensitive or runtime input files.

## Validation

- `python -m compileall src dags portal_backend`: PASS
- `python -m pytest -q`: PASS, 36 passed, 1 skipped
- `python portal/audit.py`: PASS, 0 critical issues
- `node --check portal/check_var.js`: PASS

## Prevention

`.gitignore` now also ignores:

- `data/tmp/`
- `FINAL_VERIFICATION_REPORT.md`
- `docs/brainstorming/pipeline_count_validation.md`
- `.jules/`
