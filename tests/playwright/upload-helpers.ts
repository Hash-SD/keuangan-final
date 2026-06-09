import { expect, Page } from "@playwright/test";
import path from "node:path";

export const ROOT = path.resolve(__dirname, "..", "..");
export const files = {
  pdf: path.join(ROOT, "data", "raw_lama", "pdf", "ITERA_LKTA2024Audited.pdf"),
  csvGanjil: path.join(ROOT, "data", "raw_lama", "csv", "transaksi_ganjil.csv"),
  csvGenap: path.join(ROOT, "data", "raw_lama", "csv", "transaksi_genap.csv"),
  excel: path.join(ROOT, "data", "raw_lama", "excel", "rab_prodi_sains_data.xlsx"),
};
const API_URL = "http://localhost:8091";

export async function resetSession(page: Page) {
  const response = await page.request.delete(`${API_URL}/api/upload/session/reset`);
  expect(response.ok()).toBeTruthy();
}

export async function openUploadPage(page: Page) {
  await page.goto("/#/data", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Konteks Periode Data" })).toBeVisible();
}

export async function fillContext(page: Page) {
  await page.locator("#ctx-target-tahun-akademik").fill("2025/2026");
  await page.locator("#ctx-target-tahun-anggaran").fill("2026");
  await expect(page.locator("#contextAutosaveStatus")).toContainText(/Tersimpan sementara|Belum lengkap/);
}

export async function uploadPdf(page: Page) {
  await page.locator("#upload-pdf").setInputFiles(files.pdf);
  await expect(page.locator('[data-upload-chip="pdf"]')).toContainText("ITERA_LKTA2024Audited.pdf");
}

export async function uploadCsv(page: Page) {
  await page.locator("#upload-csv").setInputFiles([files.csvGanjil, files.csvGenap]);
  await expect(page.locator('[data-upload-chip="csv"]')).toHaveCount(2);
}

export async function uploadExcel(page: Page) {
  await page.locator("#upload-excel").setInputFiles(files.excel);
  await expect(page.locator('[data-upload-chip="excel"]')).toContainText("rab_prodi_sains_data.xlsx");
}
