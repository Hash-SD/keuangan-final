# Canonical Bab IV Evidence Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove dummy production evidence and restore verifiable Bab IV performance, UAT, dashboard-detail, and figure artefacts.

**Architecture:** A read-only inventory first identifies dummy-bearing local and MinIO artefacts. A targeted cleanup then removes only confirmed dummy records/objects, preserving the active RAB bundle. Evidence collectors emit canonical output from the active bundle, while latency runs and dashboard filters are measured against that same bundle.

**Tech Stack:** Python 3.11, pandas, boto3, Flask, pytest, MinIO S3 API.

## Global Constraints

- Never delete a workbook in `data/raw/excel_lakehouse/upload-2026-06-09-011818-37cc4d`.
- Delete only artifacts whose content or identifier is confirmed dummy.
- Do not use dummy timestamps or metrics in Bab IV final evidence.
- Keep the final reconciliation status `NOT READY` for years without a same-scope source control total.

---

### Task 1: Inventory and clean confirmed dummy artefacts

**Files:**
- Create: `outputs/bab4_evidence_final/scripts/purge_dummy_evidence.py`
- Create: `outputs/bab4_evidence_final/00_manifest/dummy_cleanup_manifest.csv`

- [ ] **Step 1: Build a dry-run inventory**

Identify JSON/CSV local artefacts and MinIO JSON objects containing `dummy-` or `batch-dummy` and record path/key, matching token, and action.

- [ ] **Step 2: Verify inventory before deletion**

Run the script with `--dry-run`; confirm the active RAB session `upload-2026-06-09-011818-37cc4d` is absent from deletion targets.

- [ ] **Step 3: Delete confirmed targets**

Run the script with `--apply`; write a manifest including deletion status and timestamp.

- [ ] **Step 4: Verify cleanup**

Run a content scan and MinIO listing; assert no remaining dummy payload is used by final evidence.

### Task 2: Restore canonical measurements and UAT representation

**Files:**
- Create: `outputs/bab4_evidence_final/scripts/measure_python_pipeline_runs.py`
- Modify: `outputs/bab4_evidence_final/scripts/bab4_final_audit.py`

- [ ] **Step 1: Measure five runs**

Execute `python src/transformations/excel_lakehouse_pipeline.py` five times; persist start/end, duration, exit code, source session, output counts, and run ID.

- [ ] **Step 2: Correct UAT fallback representation**

When only the summary API is available, write one anonymised R1 submission with `question_count=5` and retain five indicators only as supporting detail.

- [ ] **Step 3: Verify canonical scope**

Assert five successful runs belong to the active RAB session and UAT output has one submission.

### Task 3: Enable and validate an item-detail dashboard scenario

**Files:**
- Modify: `portal_backend/services/local_dashboard.py`
- Modify: `tests/test_local_dashboard.py`
- Modify: `outputs/bab4_evidence_final/scripts/enrich_runtime_evidence.py`

- [ ] **Step 1: Add failing test**

Create a test asserting `item_id` query filtering returns exactly the requested Gold row.

- [ ] **Step 2: Add `item_id` to supported dashboard filters**

Extend `FILTER_COLUMNS`; retain existing filter behaviour.

- [ ] **Step 3: Validate endpoint**

Query `/api/local-dashboard/table?item_id=<deterministic-id>` and compare weighted values and lineage fields with Gold.

### Task 4: Replace invalid blank figures

**Files:**
- Modify: `outputs/bab4_evidence_final/scripts/bab4_final_audit.py`
- Modify: `outputs/bab4_evidence_final/scripts/enrich_runtime_evidence.py`

- [ ] **Step 1: Generate latency figure from five measurements**

Use duration seconds, not freshness, for the performance run chart.

- [ ] **Step 2: Mark unavailable freshness correctly**

Remove the zero-value freshness chart and write a metadata note declaring it not produced because active T0/T2 are unavailable.

- [ ] **Step 3: Generate dashboard comparison figure**

Plot Gold and dashboard amounts by scenario, rather than an all-zero difference series.

- [ ] **Step 4: Run verification**

Compile Python scripts, run focused dashboard tests, validate five rows, one UAT submission, no dummy final evidence, and non-empty applicable figures.
