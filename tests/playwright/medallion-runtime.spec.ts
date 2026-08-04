import { expect, test } from "@playwright/test";

const task = (task_id: string, state: string) => ({ task_id, state });

const runningStages = {
  raw: { total: 3, done: 3, running: 0, duration_seconds: 3 },
  bronze: { total: 3, done: 1, running: 1, duration_seconds: 5 },
  silver: { total: 3, done: 0, running: 0, duration_seconds: null },
  gold: { total: 4, done: 0, running: 0, duration_seconds: null },
  bi: { total: 5, done: 0, running: 0, duration_seconds: null },
};

const completedStages = {
  raw: { total: 3, done: 3, running: 0, duration_seconds: 3 },
  bronze: { total: 3, done: 3, running: 0, duration_seconds: 5 },
  silver: { total: 3, done: 3, running: 0, duration_seconds: 7 },
  gold: { total: 4, done: 4, running: 0, duration_seconds: 9 },
  bi: { total: 5, done: 5, running: 0, duration_seconds: 11 },
};

const activePayload = {
  status: "ready",
  active: true,
  run: {
    dag_run_id: "e2e-running-run",
    state: "running",
    start_date: "2026-08-02T10:40:00Z",
    progress: {
      available: true,
      total_tasks: 18,
      completed_tasks: 7,
      progress_pct: 39,
      current_task: "parse_flexible",
      current_state: "running",
      started_at: "2026-08-02T10:40:00Z",
      stages: runningStages,
      task_instances: [
        task("start", "success"),
        task("validate_upload_context", "success"),
        task("extract_excel_to_bronze", "success"),
        task("detect_year_and_format", "success"),
        task("parse_flexible", "running"),
        task("merge_multi_file", "queued"),
        task("normalize_silver", "queued"),
        task("map_iku_and_nomenklatur", "queued"),
        task("validate_excel_totals", "queued"),
        task("build_fact_anggaran", "queued"),
        task("write_minio_storage", "queued"),
        task("load_gold_to_postgres", "queued"),
        task("validate_trino_postgres_catalog", "queued"),
        task("refresh_superset_dataset", "queued"),
        task("refresh_superset_dashboard", "queued"),
        task("generate_storage_manifest", "queued"),
        task("generate_system_status", "queued"),
        task("end", "queued"),
      ],
    },
  },
};

const completedRun = {
  dag_run_id: "e2e-completed-run",
  state: "success",
  start_date: "2026-08-02T10:40:00Z",
  end_date: "2026-08-02T10:41:00Z",
  progress: {
    available: true,
    total_tasks: 18,
    completed_tasks: 18,
    progress_pct: 100,
    started_at: "2026-08-02T10:40:00Z",
    ended_at: "2026-08-02T10:41:00Z",
    stages: completedStages,
    task_instances: [],
  },
};

const latestPayload = { status: "ready", run: completedRun };

const runsPayload = {
  status: "success",
  runs: [completedRun, { dag_run_id: "e2e-running-run", state: "running", start_date: "2026-08-02T10:40:00Z" }],
};

test("Medallion stepper follows Airflow running and completed states", async ({ page }) => {
  await page.route("**/api/airflow/active", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(activePayload) });
  });
  await page.route("**/api/airflow/latest", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(latestPayload) });
  });
  await page.route("**/api/airflow/runs", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(runsPayload) });
  });
  await page.route("**/api/airflow/runs/**", async (route) => {
    const id = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() || "");
    const run = id === "e2e-completed-run" ? completedRun : activePayload.run;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "success", run }) });
  });

  await page.goto("/v2/#orkestrasi");

  const stepper = page.locator("#stepperContainer");
  await expect(stepper.getByText("Pipeline Sedang Berjalan")).toBeVisible();
  await expect(stepper).toContainText("7/18 task");
  await expect(stepper).toContainText("parse_flexible");
  await expect(stepper.locator(".pipeline-node.running")).toHaveCount(1);
  await expect(stepper.locator(".stage-timing.running")).toHaveCount(1);
  await expect(stepper.locator(".stage-spinner")).toHaveCount(1);
  await expect(stepper.locator(".stage-timing.idle")).toHaveCount(3);

  // Clicking the completed row must switch the stepper to that run's real
  // per-stage durations (3/5/7/9/11 s) instead of the active run's progress.
  await page.locator("#airflowPanel tr", { hasText: "e2e-completed-run" }).click();
  await expect(stepper).not.toContainText("Pipeline Sedang Berjalan");
  await expect(stepper).toContainText("3 d");
  await expect(stepper).toContainText("5 d");
  await expect(stepper).toContainText("7 d");
  await expect(stepper).toContainText("9 d");
  await expect(stepper).toContainText("11 d");
  await expect(stepper.locator(".stage-timing.running")).toHaveCount(0);
});
