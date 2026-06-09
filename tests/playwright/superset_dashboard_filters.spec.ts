import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..", "..");

test("Superset dashboard exposes unlocked native filters", async ({ page, request }) => {
  const health = await request.get("http://localhost:8089/health", { timeout: 10_000 });
  test.skip(!health.ok(), "Superset unreachable");

  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto("http://localhost:8089/login/", { waitUntil: "domcontentloaded" });
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin");
  await page.locator('input[type="submit"], button[type="submit"]').first().click();
  await page.goto("http://localhost:8089/superset/dashboard/dashboard-piutang-ukt-prodi/", { waitUntil: "domcontentloaded" });

  for (const label of ["Tahun Akademik", "Tahun Anggaran", "Semester", "Program Studi", "Kualitas Piutang"]) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  }
  for (const chart of ["Total Piutang UKT", "Jumlah Mahasiswa Penunggak", "Tren Piutang per Semester", "Piutang UKT per Prodi"]) {
    await expect(page.getByText(chart, { exact: true }).first()).toBeVisible();
  }

  await page.locator("div").filter({ hasText: /^Program Studi\*/ }).locator(".ant-select-selector").first().click();
  await expect(page.getByText("Arsitektur", { exact: true }).last()).toBeVisible();

  const report = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "reports", "superset_filters_validation.json"), "utf-8"));
  expect(report.default_filter["Program Studi"]).toEqual(["Sains Data"]);
  expect(report.has_static_lock).toBe(false);
  expect(report.charts_follow_native_filter).toBe(true);
  expect(errors).toEqual([]);
});
