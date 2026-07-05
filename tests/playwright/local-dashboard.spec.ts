import { expect, test } from "@playwright/test";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const GOLD_VIEW = resolve("data/generated/gold/vw_dashboard_piutang_ukt.csv");

const CSV = [
  "tahun_akademik,tahun_anggaran,semester,nama_prodi,nama_fakultas,kualitas,nominal_piutang_rp,jumlah_mhs_penunggak,nim,nama_debitur",
  "2023/2024,2024,Ganjil,Sains Data,Fakultas Sains,Lancar,1000000,1,120450001,Debitur A",
  "2024/2025,2025,Genap,Sains Data,Fakultas Sains,Macet,2500000,1,120450002,Debitur B",
  "2024/2025,2025,Genap,Teknik Informatika,Fakultas Teknologi,Diragukan,500000,1,120450003,Debitur C",
].join("\n");

test.beforeAll(() => {
  mkdirSync(dirname(GOLD_VIEW), { recursive: true });
  writeFileSync(GOLD_VIEW, CSV, "utf-8");
});

test.afterAll(() => {
  rmSync(GOLD_VIEW, { force: true });
});

test("local dashboard filters, charts, cross-filter, and detail table update", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto("/local-dashboard/");

  await expect(page.getByRole("heading", { name: /Dashboard Lokal/ })).toBeVisible();
  await expect(page.locator("#kpiGrid").getByText("Rp3.500.000")).toBeVisible();
  await expect(page.getByText("validated: vw_dashboard_piutang_ukt")).toBeVisible();
  await expect(page.getByText("data/generated/gold/vw_dashboard_piutang_ukt.csv")).toBeVisible();

  await page.getByLabel("Tahun Anggaran").selectOption("2025");
  await expect(page.locator("#kpiGrid").getByText("Rp2.500.000")).toBeVisible();
  await expect(page.getByTestId("local-detail-table")).toContainText("Debitur B");
  await expect(page.getByTestId("local-detail-table")).not.toContainText("Debitur A");

  await page.getByLabel("Kualitas").selectOption("Macet");
  await expect(page.getByText("Kualitas: Macet")).toBeVisible();
  await expect(page.locator("#kpiGrid").getByText("Rp2.500.000")).toBeVisible();

  await page.getByRole("button", { name: /Reset/ }).click();
  await expect(page.locator("#prodiPill").getByText("Prodi: Sains Data")).toBeVisible();
  await expect(page.locator("#kpiGrid").getByText("Rp3.500.000")).toBeVisible();

  const chart = page.getByTestId("local-chart-bar_by_tahun_anggaran");
  await expect(chart.locator("canvas")).toBeVisible();
  const box = await chart.boundingBox();
  expect(box).not.toBeNull();
  await chart.click({ position: { x: box!.width * 0.72, y: box!.height * 0.45 } });
  await expect(page.getByText("Tahun Anggaran: 2025")).toBeVisible();
  await expect(page.getByTestId("local-detail-table")).toContainText("Debitur B");

  expect(consoleErrors).toEqual([]);
});
