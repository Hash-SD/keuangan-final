# Bolt Performance Finish Report

Generated: 2026-06-30

## Scope

Final finishing pass focused on one small, measurable performance improvement without new dependencies, architectural changes, or package configuration changes.

## Skills Used

- `diagnosing-bugs`: used to build a measurement loop before changing code.
- `performance`: used to prioritize low-risk web/API performance wins.
- `ai-research-reproduction` / `minimal-run-and-audit`: used only for auditable-run discipline; the full paper reproduction protocol is not applicable to this lakehouse application.

## Baseline

Evidence: `outputs/evidence/bolt_lakehouse_summary_baseline.json`

- `lakehouse_summary()` median: `0.43220019999716897` seconds.
- The endpoint read full `data/generated/gold/fact_anggaran.csv` only to get row count and weighted total.
- Full CSV size: `876192` bytes.
- Gold Parquet size: `51567` bytes.

## Optimization

Changed `portal_backend/services/lakehouse.py` so `lakehouse_summary()` reuses `truth["reconciliation"]` values already computed by `build_system_truth_status`.

This removes a duplicate fact table read from the endpoint while preserving:

- `gold.fact_rows = 1010`
- `gold.fact_anggaran_total_weighted = 913391665.0`

Also fixed a portal audit false positive so CSS `var(...)` is not reported as JavaScript `var`, and changed the Google Material Symbols font URL from `display=block` to `display=swap`.

## After

Evidence: `outputs/evidence/bolt_lakehouse_summary_after.json`

- `lakehouse_summary()` median: `0.3983399999997346` seconds.
- Expected endpoint improvement: about `7.8%` for the measured local call.
- Fact table duplicate read: removed.
- Endpoint output values: unchanged.

## Verification

PASS:

- `python -m compileall src dags portal_backend`
- `python -m pytest -q`
- `python portal/audit.py` from the `portal` directory
- `node --check portal/check_var.js`

Latest pytest:

- 34 passed
- 1 skipped
- 1 pandas FutureWarning

## Known Notes

- `npm test` is not a valid frontend test in this repo because `package.json` still contains the placeholder script `echo "Error: no test specified" && exit 1`.
- The pandas FutureWarning remains non-critical and pre-existing.
