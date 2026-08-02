# Unified Medallion Pipeline Progress

## Goal

Make `Tahapan Pemrosesan Medallion` the single source of visible pipeline
progress. Remove the duplicate progress block from `Eksekusi Pemrosesan Data`.

## User experience

- The Medallion card header shows the Airflow task count, percentage, active task,
  and runtime.
- While the DAG is active, the header uses a compact blue progress bar with a
  restrained shimmer and a status spinner.
- Each layer reflects its Airflow stage state: running uses a spinner, completed
  uses a green check, pending uses a neutral state, and failed uses an error state.
- When the DAG reaches a terminal success state, the global indicator becomes a
  green check and keeps the Airflow-derived layer durations visible.
- Failure is visible in the same card with a red status and no success icon.

## Data flow

The UI reuses the existing Airflow `progress` payload. No new endpoint or client
duration calculation is introduced. `renderLiveStepper` renders the summary and
the five layer nodes in one DOM update, so the same active/latest priority and
selected-run fallback remain intact.

## Performance and accessibility

- Remove the old `progressHtml` block from `renderAirflowPanel`.
- Avoid an additional polling loop or animation timer; CSS animation is used only
  while a stage is active.
- Use semantic status text and `role="status"` for live updates.
- Respect `prefers-reduced-motion` in the progress shimmer and stage spinner.
- Keep all values escaped through the existing `safe` helper.

## Verification

- Contract test confirms the old progress block is gone and the unified renderer
  contains task count, percentage, runtime, and live status states.
- Runtime smoke test covers latest success values, active-run spinner priority,
  and failed-run presentation.
- Existing Airflow duration tests continue to verify that all durations originate
  from Airflow task data.
