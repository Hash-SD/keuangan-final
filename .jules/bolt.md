## 2026-06-30 - Nomenklatur Candidate Normalization Was Not Hot
**Learning:** The obvious repeated-normalization path in `budget_cleaning.py` is cold for the current uploaded dataset because most rows already carry IKU codes before keyword fallback. A benchmark of `clean_and_enrich_budget_items` on 375 rows showed only 248 `normalize_match_text` calls and ~0.067s median runtime, so caching that path would be premature.
**Action:** Prefer profiling portal/API or Excel extraction paths before optimizing mapping fallback code.
