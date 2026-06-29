# Legacy Cleanup Verification

Status: `PARTIAL`

Legacy PDF/CSV/piutang files still exist under `src/generators`, `src/extraction`, `data/raw_lama`, and compatibility SQL loader skips old piutang gold tables when absent. They are not the clean-run source for `fact_anggaran`, but legacy code has not been fully moved to `src/legacy` or deleted.
