# Removed Legacy Files

Branch: `feature/excel-lakehouse-v2-final`

No legacy files were physically deleted in this pass.

Legacy PDF/CSV/piutang modules are no longer the default pipeline, but remain in the branch to avoid breaking existing imports, historical tests, and platform fallback routes before a separate aggressive cleanup pass.

Legacy domains marked for later removal:

- `src/extraction/extract_pdf_piutang.py`
- `src/generators/generate_pdf_audited.py`
- `src/transformations/gold_star_schema.py`
- `dags/keuangan_prodi_lakehouse_dag.py`
- Superset piutang scripts/routes that are still referenced by tests
- PDF/CSV upload compatibility endpoints after portal replacement is fully verified
