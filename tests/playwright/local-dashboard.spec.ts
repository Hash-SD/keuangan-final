import { expect, test } from "@playwright/test";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const GOLD_VIEW = resolve("data/generated/gold/fact_anggaran.csv");
const hadOriginal = existsSync(GOLD_VIEW);
const originalContent = hadOriginal ? readFileSync(GOLD_VIEW, "utf-8") : null;

const CSV = [
  "item_id,dataset_session_id,run_id,tahun,prodi,fakultas,iku,kode_iku,kegiatan,akun,uraian_detail,jumlah,allocation_weight,jumlah_weighted_iku,mapping_status,source_file",
  "item-001,dataset-e2e,run-e2e,2024,Sains Data,Fakultas Sains,IKU-1,IKU-1,Kegiatan A,Belanja Bahan,Detail A,1000000,1,1000000,VALID,rab-2024.xlsx",
  "item-002,dataset-e2e,run-e2e,2025,Sains Data,Fakultas Sains,IKU-2,IKU-2,Kegiatan B,Belanja Jasa,Detail B,2500000,1,2500000,VALID,rab-2025.xlsx",
  "item-003,dataset-e2e,run-e2e,2025,Teknik Informatika,Fakultas Teknologi,IKU-3,IKU-3,Kegiatan C,Belanja Modal,Detail C,500000,1,500000,VALID,rab-2025.xlsx",
].join("\n");

test.beforeAll(() => {
  mkdirSync(dirname(GOLD_VIEW), { recursive: true });
  writeFileSync(GOLD_VIEW, CSV, "utf-8");
});

test.afterAll(() => {
  if (hadOriginal && originalContent !== null) writeFileSync(GOLD_VIEW, originalContent, "utf-8");
  else rmSync(GOLD_VIEW, { force: true });
});

test("local dashboard filters, charts, cross-filter, and detail table update", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto("/local-dashboard/");

  await expect(page.getByRole("heading", { name: /Dashboard Anggaran RAB\/IKU/ })).toBeVisible();
  await expect(page.locator("#kpiGrid").getByText("Rp4.000.000")).toBeVisible();
  await expect(page.getByText("validated: fact_anggaran")).toBeVisible();
  await expect(page.getByText("data/generated/gold/fact_anggaran.csv")).toBeVisible();

  await page.getByLabel("Tahun").selectOption("2025");
  await expect(page.locator("#kpiGrid").getByText("Rp3.000.000")).toBeVisible();
  await expect(page.getByTestId("local-detail-table")).toContainText("Detail B");
  await expect(page.getByTestId("local-detail-table")).not.toContainText("Detail A");

  await page.getByLabel("Prodi").selectOption("Sains Data");
  await expect(page.locator("#kpiGrid").getByText("Rp2.500.000")).toBeVisible();
  await expect(page.locator("#prodiPill").getByText("Prodi: Sains Data")).toBeVisible();

  await page.getByRole("button", { name: /Reset/ }).click();
  await expect(page.locator("#kpiGrid").getByText("Rp4.000.000")).toBeVisible();

  const chart = page.getByTestId("local-chart-anggaran_per_tahun");
  await expect(chart.locator("canvas")).toBeVisible();
  await chart.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1200);
  const point = await chart.evaluate((element) => {
    const instance = (window as typeof window & { echarts: any }).echarts.getInstanceByDom(element);
    const option = instance.getOption();
    const value = option.series[0].data[1];
    const top = instance.convertToPixel({ xAxisIndex: 0, yAxisIndex: 0 }, [1, value]);
    const bottom = instance.convertToPixel({ xAxisIndex: 0, yAxisIndex: 0 }, [1, 0]);
    const rect = element.getBoundingClientRect();
    return { x: rect.x + top[0], y: rect.y + (top[1] + bottom[1]) / 2 };
  });
  await page.mouse.click(point.x, point.y);
  await expect(page.getByText("Tahun: 2025")).toBeVisible();
  await expect(page.getByTestId("local-detail-table")).toContainText("Detail B");

  expect(consoleErrors).toEqual([]);
});
