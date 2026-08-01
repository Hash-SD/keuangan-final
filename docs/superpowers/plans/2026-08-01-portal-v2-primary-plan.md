# Portal V2 Primary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Make `portal/v2/index.html` the functional primary portal while preserving V1 at `/legacy` and retaining all verified data, upload, orchestration, review, dashboard, and UAT capabilities.

**Architecture:** Keep the existing Flask/static-serving model. Add an explicit primary/legacy route mapping in the backend, make V2 resolve the backend API port correctly in local and reverse-proxy deployments, and use the existing authoritative APIs for every metric and status. Extend the V2 page with the missing V1 workflows using the V2 design tokens and component patterns.

**Tech Stack:** Flask, vanilla HTML/CSS/JavaScript, existing portal backend APIs, pytest, browser smoke tests.

## Global Constraints

- V2 must read live values from `/api/superset/summary`, `/api/metrics`, `/api/airflow/latest`, `/api/system-truth/status`, and `/api/excel-lakehouse/status`.
- V1 remains available at `/legacy` until V2 smoke tests pass.
- No credentials or API tokens may be embedded in HTML.
- Failed, running, missing, and unreachable states must be visually distinct and truthful.
- Preserve unrelated user changes and runtime artifacts.

### Task 1: Primary and legacy route contract

**Files:**
- Modify: `portal_backend/app.py` static route handling
- Modify: `portal/index.html` only if legacy navigation needs a stable link
- Test: `tests/test_portal_routes.py`

- [ ] Add failing tests asserting `/` serves V2 content, `/legacy` serves the existing V1 content, and `/v2/` remains directly accessible during migration.
- [ ] Run `python -m pytest tests/test_portal_routes.py -q` and verify the new route tests fail before implementation.
- [ ] Implement explicit route behavior without deleting or overwriting `portal/index.html`; use `portal/v2/index.html` for `/` and expose the previous file at `/legacy`.
- [ ] Run the focused route tests and verify they pass.

### Task 2: V2 live data adapter and status model

**Files:**
- Modify: `portal/v2/index.html` API base resolution, state loading, metric rendering, status rendering
- Test: `tests/test_portal_v2_contract.py`

- [ ] Add failing contract tests requiring API base resolution for ports 8090/8190, calls to all five authoritative endpoints, live metric field mapping, and non-hardcoded pipeline status.
- [ ] Run the focused contract tests and verify failure.
- [ ] Implement a V2 adapter that maps API payloads into one immutable view model with explicit loading, ready, failed, missing, and unreachable states.
- [ ] Replace placeholder `-` KPI values and static `Ready` stepper values with live values and timestamps; show a clear fallback message when APIs are unavailable.
- [ ] Run focused frontend contract tests and verify pass.

### Task 3: V2 feature parity and UI/UX completion

**Files:**
- Modify: `portal/v2/index.html`
- Test: `tests/test_portal_v2_contract.py`

- [ ] Add failing assertions for Upload, Orkestrasi, Review IKU, Lakehouse lineage, Dashboard links, Analytics/UAT, and Status System sections.
- [ ] Implement the missing sections with V2 Apple-style tokens, responsive layout, keyboard-visible controls, localized error states, and the Review IKU instruction: save overrides, then open Orkestrasi → Jalankan Sistem.
- [ ] Wire existing upload, Airflow trigger/polling, IKU override, UAT submit, preview, and dashboard link endpoints without duplicating backend business logic.
- [ ] Run the focused contract tests and verify pass.

### Task 4: Runtime and browser verification

**Files:**
- Modify: `tests/test_portal_v2_contract.py` only for discovered regression coverage
- Modify: `docker-compose.yml` only if the primary route requires a static-server configuration change

- [ ] Run `python -m compileall -q portal_backend` and `git diff --check`.
- [ ] Run the complete deterministic portal/API test subset and record output.
- [ ] Start/recreate portal services, then browser-smoke `/`, `/legacy`, upload view, orchestration, Review IKU, Lakehouse, Analytics, Dashboard, and Status System.
- [ ] Confirm live cards show current Superset totals, Gold rows, Quality Gate, and authoritative pipeline status; confirm no browser console errors or mojibake.
- [ ] Run the broad test suite with a bounded timeout; report any pre-existing timeout separately instead of claiming success.
