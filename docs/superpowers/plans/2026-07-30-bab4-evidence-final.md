# Bab IV Evidence Final Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce reproducible, source-traceable empirical evidence for the final Bab IV structure without altering source workbooks or prior evidence.

**Architecture:** New audit scripts read the active workbook bundle, current Bronze/Silver/Gold artifacts, runtime services, portal UAT records, and Airflow metadata. They write only to `outputs/bab4_evidence_final/`, preserving historical outputs and explicitly labeling unavailable evidence.

**Tech Stack:** Python 3.11, pandas, openpyxl, matplotlib, Docker Compose CLIs, Airflow CLI, PostgreSQL `psql`, HTTP endpoints, local Parquet/CSV/JSON.

## Global Constraints

- Do not modify workbooks, production pipeline code, or historical evidence directories.
- Use current local artifacts as the primary source of truth.
- Keep UAT as single-expert acceptance testing; do not generalize to a population.
- Use `jumlah_weighted_iku` for IKU-level aggregations.
- Write every new artifact under `outputs/bab4_evidence_final/`.
- Mark evidence `READY`, `READY WITH LIMITATIONS`, or `NOT READY`.

---

### Task 1: Isolated audit scaffold and reproducibility manifest

**Files:**
- Create: `outputs/bab4_evidence_final/scripts/bab4_final_audit.py`
- Create: `outputs/bab4_evidence_final/00_manifest/*`

- [ ] Record Git identity, runtime versions, source hashes, and command outcomes.
- [ ] Read only the active dataset pointer and current generated artifacts.
- [ ] Preserve all pre-existing worktree changes.

### Task 2: Source workbook, business-rule, and Gold-lineage evidence

**Files:**
- Create: `outputs/bab4_evidence_final/01_perancangan/411_analisis_sumber/*`
- Create: `outputs/bab4_evidence_final/01_perancangan/412_arsitektur_aturan/*`
- Create: `outputs/bab4_evidence_final/01_perancangan/413_gold_lineage/*`

- [ ] Profile workbook and sheet structure, including hidden elements and classification indicators.
- [ ] Extract business-rule references from implementation code.
- [ ] Validate Gold schema, grain, dimensions, and deterministic lineage samples.

### Task 3: Per-period reconciliation and quality metrics

**Files:**
- Create: `outputs/bab4_evidence_final/03_pengujian/431_kualitas_rekonsiliasi/*`
- Create: `outputs/bab4_evidence_final/figures/fig_431_*`

- [ ] Compute 2023 Jan-Jun, 2023 Jul-Dec, total 2023, 2024, 2025, and overall reconciliation from matching scopes.
- [ ] Separate expected exclusions from quality-related exclusions.
- [ ] Compute Gold completeness, validity, consistency, mapping, reconciliation, and traceability on compatible units.

### Task 4: Runtime, Airflow, storage/query, and dashboard evidence

**Files:**
- Create: `outputs/bab4_evidence_final/02_implementasi/421_lingkungan_orkestrasi/*`
- Create: `outputs/bab4_evidence_final/02_implementasi/423_gold_dashboard/*`
- Create: `outputs/bab4_evidence_final/03_pengujian/432_kinerja_dashboard/*`

- [ ] Extract actual DAG runs and task instances.
- [ ] Verify each storage/query system independently and label its data state.
- [ ] Compare dashboard endpoints to Gold under reproducible filters where supported.
- [ ] Measure freshness only where T0, T1, and T2 are sourceable.

### Task 5: UAT portal provenance and method alignment

**Files:**
- Create: `outputs/bab4_evidence_final/03_pengujian/433_uat/*`

- [ ] Collect portal UAT submission evidence, anonymize evaluator identity, and retain timestamps/IDs.
- [ ] Separate portal submission records from generator-generated summaries.
- [ ] Write the 7-dimension versus 5-indicator method alignment report.

### Task 6: Final Bab IV map, tables, figures, and honest validation status

**Files:**
- Create: `outputs/bab4_evidence_final/evidence_index.md`
- Create: `outputs/bab4_evidence_final/bab4_evidence_summary.md`
- Create: `outputs/bab4_evidence_final/final_validation_report.md`
- Create: `outputs/bab4_evidence_final/section_evidence_map_final.*`

- [ ] Produce CSV and LaTeX tables, plus PNG/PDF/CSV/JSON chart bundles when data exists.
- [ ] Request, but never fabricate, screenshots.
- [ ] Report status per required subsection and list limitations.

## Self-Review

- Scope covers UAT provenance, reconciliation, quality, freshness, Airflow, storage/query, dashboard, profiling, rules, lineage, dropout, tables, figures, final mapping, legacy exclusions, and reproducibility.
- No production paths are write targets.
- No completion status is inferred from configuration or container status alone.
