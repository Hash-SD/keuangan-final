import { expect, test } from "@playwright/test";

const task = (task_id: string, state: string) => ({ task_id, state });

const activeRuntime = {
  status: "ready",
  active: true,
  active_run: {
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
      stages: {
        raw: { total: 3, done: 3, running: 0, duration_seconds: 0.3 },
        bronze: { total: 3, done: 1, running: 1, duration_seconds: 0.4 },
        silver: { total: 3, done: 0, running: 0, duration_seconds: null },
        gold: { total: 4, done: 0, running: 0, duration_seconds: null },
        bi: { total: 5, done: 0, running: 0, duration_seconds: null },
      },
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
  latest_run: null,
  runtime_run: null,
  source: "active",
};

const completedRuntime = {
  status: "ready",
  active: false,
  active_run: null,
  latest_run: {
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
      stages: {
        raw: { total: 3, done: 3, running: 0, duration_seconds: 0.3 },
        bronze: { total: 3, done: 3, running: 0, duration_seconds: 0.4 },
        silver: { total: 3, done: 3, running: 0, duration_seconds: 1 },
        gold: { total: 4, done: 4, running: 0, duration_seconds: 0.8 },
        bi: { total: 5, done: 5, running: 0, duration_seconds: 0.5 },
      },
      task_instances: [],
    },
  },
  runtime_run: null,
  source: "latest",
};

test("Medallion stepper follows Airflow running and completed states", async ({ page }) => {
  let runtimePayload: typeof activeRuntime | typeof completedRuntime = activeRuntime;

  await page.route("**/api/airflow/runtime", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(runtimePayload),
    });
  });

  await page.goto("/v2/#orkestrasi");

  const stepper = page.locator("#stepperContainer");
  await expect(stepper.getByText("Pipeline sedang berjalan")).toBeVisible();
  await expect(stepper).toContainText("7/18 task");
  await expect(stepper).toContainText("Task aktif: parse_flexible");
  await expect(stepper).toContainText("Menunggu 3 task Airflow");
  await expect(stepper.locator(".pipeline-node.running")).toHaveCount(1);
  await expect(stepper.locator(".node-task-detail")).toHaveCount(5);

  runtimePayload = completedRuntime;
  await page.reload();

  await expect(stepper.getByText("Pipeline selesai")).toBeVisible();
  await expect(stepper.locator(".medallion-progress-summary")).toHaveCount(1);
  await expect(stepper.locator(".pipeline-progress-value")).toContainText("100%");
  await expect(stepper.locator(".pipeline-progress-value")).not.toContainText("18/18 task");
  await expect(stepper.locator(".pipeline-progress-value")).not.toContainText("Â");
  await expect(stepper).toContainText("0.3s");
  await expect(stepper).toContainText("0.5s");
  await expect(stepper.locator(".pipeline-node.running")).toHaveCount(0);
  await expect(stepper.locator(".node-task-detail")).toHaveCount(0);
});
