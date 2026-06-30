# Parser Amount Column Fix Verification

Generated at: 2026-06-30

## Scope

This report records the fix for the RAB parser issue where 2023/2024 workbooks could use the first `Total` column (`Total Sebelum Pajak`) or tax/header cells instead of the final budget amount.

## Skills And MCP Used

- `find-skills`: used to discover spreadsheet/parser debugging support.
- `diagnosing-bugs`: used for a reproduce-fix-verify loop around the parser defect.
- `spreadsheets`: used as guidance for workbook-aware inspection.
- Context7 MCP: queried OpenPyXL documentation for safe workbook loading/iteration behavior (`load_workbook`, `read_only`, `data_only`).

## Code Changes

- `src/parser_flexible/rab_parser.py`
  - Selects final amount columns by semantic priority and right-most tie-break.
  - Maps `Harga Satuan` before `Satuan`.
  - Avoids treating data text containing `Belanja` as a table header.
  - Prevents header rows such as `Uraian` from becoming budget items.
  - Tightens total-row detection so IKU text containing `Jumlah` is not treated as a subtotal row.
  - Separates `REKAP_FINAL_TOTAL`, `REKAP_ACCOUNT_ROW`, and `SHEET_TOTAL_ROW` evidence.

## Evidence

Evidence file: `outputs/evidence/parser_amount_fix_validation.json`

Current regenerated totals from real uploaded Excel files:

| Year | Silver item rows | Weighted Gold total |
| --- | ---: | ---: |
| 2023 | 62 | 127,027,000 |
| 2024 | 113 | 154,588,390 |
| 2025 | 284 | 898,369,481 |

Quality checks after clean-run:

- Silver missing amount rows: 0
- Header-like `uraian` rows in Silver: 0
- Small positive header-artifact amount rows: 0
- 2023 Jan-Jun rekap status: OK
- 2023 Jul-Des rekap status: OK
- 2024 rekap status: REVIEW, because workbook rekap total is 164,849,800 while parsed detail total is 154,588,390. This variance is intentionally visible and not hidden.

## Regression Test

Added `tests/test_rab_parser_amount_columns.py` to assert:

- 2024 detail rows are 113 and total 154,588,390.
- 2023 combined detail rows are 62 and total 127,027,000.
- No parsed budget item has missing `jumlah`.
- No table header row (`Uraian`) is parsed as a budget item.
- No small header-artifact amount rows are accepted.
