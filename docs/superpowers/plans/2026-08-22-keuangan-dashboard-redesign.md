# Keuangan Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the SILARAS finance dashboard from a repetitive, technically exposed Superset mirror into a readable editorial-operational dashboard while preserving data contracts and interactions.

**Architecture:** Keep the existing Flask proxy, vanilla JavaScript, ECharts, and CSS token system. Put display-only vocabulary and numeric classification in `dashboard-presentation.js`, keep chart/table rendering behavior in `app.js`, and use CSS tokens/components for the hierarchy and surfaces. Verify the visible route with Playwright so an old bundle or alternate surface cannot silently pass.

**Tech Stack:** Vanilla JavaScript, ECharts, CSS custom properties, Flask proxy, Node test runner, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-08-22-keuangan-dashboard-redesign-design.md`

## Global Constraints

- Do not change Superset endpoints, dataset lineage, Gold data, filters, or chart payload shapes.
- Do not run pipeline, upload, Airflow trigger, publish, or Docker mutation commands.
- Keep `source_file` and other lineage values exact; only display labels and status copy may be normalized.
- Use TDD for every behavior change: write a failing test, observe the failure, implement the smallest fix, then rerun the focused and regression suites.
- Use sentence case for visible labels and tabular numerals for numeric values; do not expose snake_case in visible headers.
- Preserve loading, empty, error, partial, sorting, search, pagination, theme, keyboard focus, and reduced-motion behavior.

---

### Task 1: Lock the presentation and build identity contract

**Files:**
- Modify: `superset-dashboard/public/dashboard-presentation.js`
- Modify: `superset-dashboard/public/index.html`
- Test: `tests/dashboard-presentation.test.js`
- Test: `tests/playwright/superset-dashboard.spec.ts`

**Interfaces:**
- `displayTitle(title: unknown): string` removes the display-only brand prefix and normalizes known title vocabulary.
- `displayColumnLabel(value: unknown): string` maps known technical keys and humanizes unknown snake_case keys.
- `isCountColumn(value: unknown): boolean` classifies count columns without treating `jumlah` amounts as counts.

- [x] **Step 1: Write failing tests for stale-surface-visible contracts.** Add assertions for sentence-case labels, no `SILARAS |` title prefix, `Klaster Kegiatan`, count classification, and a page marker such as `data-ui-version` on the current public entrypoint.
- [x] **Step 2: Run the focused tests and confirm the expected RED failures.** Run `rtk node --test tests/dashboard-presentation.test.js` and `rtk npm run test:playwright -- tests/playwright/superset-dashboard.spec.ts`; the new assertions must fail before the implementation.
- [x] **Step 3: Implement the smallest display contract.** Keep the helper module framework-free, add a visible `data-ui-version` or equivalent cache-busting marker to `index.html`, and ensure `app.js` consumes the helper for every title/header path.
- [x] **Step 4: Run the focused tests and confirm GREEN.** Re-run the Node and Playwright commands, then inspect the browser DOM for no prefixed headings and no underscored headers.

### Task 2: Rebalance typography, surfaces, and responsive rhythm

**Files:**
- Modify: `superset-dashboard/public/styles.css`
- Test: `tests/playwright/superset-dashboard.spec.ts`

**Interfaces:**
- CSS tokens remain the single source for colors, radii, shadows, spacing, and type roles.
- Existing classes (`.metric-card`, `.glass-card`, `.chart-card`, `.apple-table`) remain stable for JavaScript and tests.

- [x] **Step 1: Add failing browser assertions for the visual contract.** Assert sentence-case metric labels, tabular numeric styling, the primary KPI modifier, desktop max-width, mobile single-column layout, and absence of page-level horizontal overflow.
- [x] **Step 2: Run Playwright to observe RED.** Use the local dashboard URL on desktop and a mobile project/viewport; record the exact failing selectors rather than weakening assertions.
- [x] **Step 3: Apply the CSS direction.** Use Plus Jakarta Sans with a stronger display scale, remove broad all-caps transforms, introduce medium/semibold hierarchy, make the primary KPI span two grid tracks when space permits, vary inner/outer radii, tint shadows teal, keep chart colors restrained, add `font-variant-numeric: tabular-nums`, and add reduced-motion rules.
- [x] **Step 4: Verify GREEN and visually inspect screenshots.** Run desktop and mobile Playwright checks, then capture the full page and inspect top hierarchy, tables, treemap, footer, focus state, and dark mode.

### Task 3: Convert status and KPI hierarchy into useful information density

**Files:**
- Modify: `superset-dashboard/public/app.js`
- Modify: `superset-dashboard/public/index.html`
- Modify: `superset-dashboard/public/styles.css`
- Test: `tests/playwright/superset-dashboard.spec.ts`

**Interfaces:**
- `orderedVisibleCharts()` continues to control stable business ordering.
- A status renderer consumes existing chart payload records and returns display-only status content; it never mutates the payload.

- [x] **Step 1: Add failing tests for KPI priority and one-row status rendering.** Assert that the primary total card has the primary modifier, count cards remain secondary, a single `OK` reconciliation result renders as a compact status strip, and the old full-width status table is not rendered as a dominant card.
- [x] **Step 2: Run the focused Playwright test and confirm RED.** Capture the current card classes and status DOM so the failure proves the old structure is still present.
- [x] **Step 3: Implement display-only hierarchy.** Add a primary modifier to the total-budget KPI, keep available count KPIs, collapse one-row status data into a labeled status strip with a badge and explanatory copy, and leave multi-row validation data in a table for audit use.
- [x] **Step 4: Run GREEN and check filter/error behavior.** Verify status changes for success/warning/error payloads and ensure an API failure still uses the existing inline error state.

### Task 4: Improve chart order, treemap emphasis, and utility controls

**Files:**
- Modify: `superset-dashboard/public/app.js`
- Modify: `superset-dashboard/public/treemap-data.js`
- Modify: `superset-dashboard/public/styles.css`
- Test: `tests/treemap-data.test.js`
- Test: `tests/playwright/superset-dashboard.spec.ts`

**Interfaces:**
- `buildTreemapData(records, options)` remains deterministic and returns ranked groups with an explicit remainder marker.
- Existing chart sort controls continue to call `renderChart(spec)` and do not mutate records.

- [x] **Step 1: Add failing tests for remainder emphasis and chart utility density.** Assert that the remainder group is marked separately, that the highest-value named groups remain before it, and that feature chart controls retain accessible labels without duplicating decorative UI.
- [x] **Step 2: Run Node and Playwright tests to confirm RED.** Run the treemap unit test and dashboard E2E test before changing the rendering.
- [x] **Step 3: Implement the smallest visualization changes.** Keep top named groups readable, style the remainder as a quieter “Lainnya” node, preserve actual totals, and reduce repeated sort-control prominence without removing sorting.
- [x] **Step 4: Verify GREEN with desktop and narrow screenshots.** Confirm labels do not collide, chart canvases remain visible, and the treemap does not create overflow.

### Task 5: Finish table vocabulary, density, and audit-friendly lineage display

**Files:**
- Modify: `superset-dashboard/public/app.js`
- Modify: `superset-dashboard/public/dashboard-presentation.js`
- Modify: `superset-dashboard/public/styles.css`
- Test: `tests/dashboard-presentation.test.js`
- Test: `tests/test_superset_dashboard_format.py`
- Test: `tests/playwright/superset-dashboard.spec.ts`

**Interfaces:**
- Table headers use `displayColumnLabel()`; raw column keys remain available to `formatValueForColumn()` and row lookup.
- `formatValueForColumn(value, columnName)` distinguishes counts, currency, years, statuses, and identifiers.

- [x] **Step 1: Add failing tests for every visible table family.** Cover yearly summary counts without `Rp`, nominal columns with `Rp`, Indonesian labels for all known technical keys, exact source filenames, and no visible underscored header.
- [x] **Step 2: Run Node, pytest, and Playwright tests to confirm RED.** Use focused commands for the new assertions and keep the failure output as evidence of the old behavior.
- [x] **Step 3: Implement label and format rules.** Expand the semantic label map, use sentence case in table headers, make source filenames visually secondary while preserving exact text, and keep technical columns hidden or behind the audit table where the existing contract allows.
- [x] **Step 4: Run GREEN and inspect the detail/validation tables.** Confirm pagination, search, sort, sticky headers, numeric alignment, and no horizontal page overflow.

### Task 6: Verify, document, and hand off the redesign

**Files:**
- Modify: `docs/AI-CODEBASE-GUIDE.md`
- Modify: `superset-dashboard/README.md`
- Test: `tests/dashboard-presentation.test.js`
- Test: `tests/test_superset_dashboard_format.py`
- Test: `tests/playwright/superset-dashboard.spec.ts`

- [x] **Step 1: Run static checks.** Run `rtk node --check` for changed JavaScript files and `rtk git diff --check`.
- [x] **Step 2: Run focused regression suites.** Run `rtk node --test tests/dashboard-presentation.test.js tests/treemap-data.test.js`, the focused Superset pytest bridge/format tests, and the targeted Playwright spec.
- [x] **Step 3: Run browser visual QA.** Start the local mirror on the configured dev port, inspect desktop and mobile screenshots, check console errors/warnings, and stop the server after verification.
- [x] **Step 4: Update documentation.** Record the presentation contract, UI version marker, label normalization, status treatment, and verification commands in the codebase guide and dashboard README.
- [x] **Step 5: Review the diff.** Confirm only dashboard presentation, related tests, and documentation changed; do not include data/output artifacts or secrets.
