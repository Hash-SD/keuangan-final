# Data Cleaning and Dashboard Redesign Verification

Generated at: 2026-06-29

## Scope

This verification covers the UI/data issues reported on the local portal and Superset dashboard:

- `UNMAPPED_IKU` / `UNMAPED` labels in Superset.
- Raw pipe-delimited (`|`) parser text leaking into filters and charts.
- Price-like values such as `900000`, `450000`, and `180000` being treated as account codes.
- Orchestration page showing `Execution Time` as `488 jam...` from a legacy latency calculation.
- Superset KPI `Total Anggaran` double-counting multi-IKU rows.

## Skills Used

- `find-skills`: used to locate/install the requested support skills.
- `brainstorming`: used to audit the current state and present an approved implementation design before code changes.
- `apache-superset`: used as the dashboard integration guidance; local Superset was controlled through the repository's existing API script.
- `browser:control-in-app-browser`: used for visual verification of the local portal and Superset dashboard.

## Implemented Changes

### Pipeline Cleaning

- Added `src/transformations/budget_cleaning.py`.
- Enriched Silver RAB rows before Gold generation.
- Cleaned display text for `kegiatan`, `cluster_kegiatan`, `akun`, `nama_akun`, `iku`, and dashboard-facing labels.
- Rejected account codes unless they match valid account prefixes (`51`, `52`, `53`, `57`).
- Prevented item-row price values from replacing account context.
- Added conservative Nomenklatur-based IKU enrichment using exact/source IKU first, then high-confidence token/fuzzy matching.
- Rows without sufficient IKU confidence are marked `IKU_REVIEW_REQUIRED`, not forced into a fake IKU.

### Gold and Dashboard Metrics

- Removed `UNMAPPED_IKU` fallback from `fact_anggaran`.
- Dashboard IKU view now excludes rows without valid `kode_iku`.
- Superset filters use clean fields.
- Superset aggregation uses `jumlah_weighted_iku` for `Total Anggaran` to prevent multi-IKU double-counting.

### Portal Orchestration

- Replaced misleading `Execution Time` label with `Source to Gold`.
- Fixed latency artifacts to use Excel Lakehouse outputs:
  - `fact_anggaran.csv`
  - `vw_dashboard_iku_anggaran.csv`
  - `vw_dashboard_detail_item.csv`
  - `excel_lakehouse_metadata.json`
- Fixed source timing to prefer `active_excel_lakehouse_dataset.json` over legacy PDF/CSV pointers.

### Test Stability

- Updated latency tests from legacy piutang artifacts to Excel Lakehouse artifacts.
- Made upload-session JSON restore/write paths atomic on Windows.
- Made backend `write_json` atomic with retry.

## Evidence

- Data profile after cleanup: `outputs/evidence/data_cleaning_profile_after.json`
- Database/data check: `outputs/evidence/data_cleaning_db_check.json`
- Final pytest output: `outputs/evidence/final_test_output.txt`
- Portal screenshot: `outputs/evidence/portal_screenshots/orkestrasi_source_to_gold_loaded.png`
- Superset screenshot: `outputs/evidence/superset_screenshots/dashboard_weighted_final.png`

## Verified Results

- `fact_anggaran` rows: 361
- Unique budget items: 277
- Dashboard IKU rows: 8
- `UNMAPPED/UNMAPED` in dashboard fields: 0
- Raw pipe (`|`) in dashboard fields: 0
- Long dashboard activity labels over 120 chars: 0
- Long account labels over 80 chars: 0
- Superset Kegiatan filter options after text cleanup: 12
- Superset Akun filter options after text cleanup: 10
- Total unique item amount: 935,795,331
- Total weighted IKU amount: 935,795,331
- Superset `Executive KPI - Total Anggaran`: 935,795,331
- Portal latency source basis: `active_excel_lakehouse_dataset`
- Portal Source to Gold: 3,075 seconds / 51 minutes 15 seconds

## Text-Only Cleanup Addendum

A second display audit was run after the dashboard looked cleaner but still had overly long labels in `kegiatan`, `akun`, and `nama_akun`.

Additional changes:

- `kegiatan` and `cluster_kegiatan` now keep the activity code and main activity name only.
- Item-level detail remains in `uraian_detail`.
- `akun` now uses `kode_akun - nama akun baku`, for example `524111 - Belanja Perjalanan Dinas`.
- Financial fields were not changed.

Evidence:

- Before profile: `outputs/evidence/text_display_profile_before.json`
- After profile: `outputs/evidence/text_display_profile_after.json`
- SQL check: `outputs/evidence/text_display_db_check.json`
- Visual check: `outputs/evidence/superset_screenshots/dashboard_text_clean_final.png`

## Remaining Data Limitations

- 255 fact rows remain `needs_review` for IKU because the available RAB labels do not match the Nomenklatur strongly enough. These are intentionally not mapped to avoid fabricated IKU assignments.
- 2 source items remain missing valid account code and are flagged `MISSING_ACCOUNT;IKU_REVIEW_REQUIRED`.

## Final Test Result

`python -m pytest`: 70 passed, 1 skipped.
