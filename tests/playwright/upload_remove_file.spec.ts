import { expect, test } from "@playwright/test";
import { files, fillContext, openUploadPage, resetSession, uploadExcel, uploadPdf } from "./upload-helpers";

test("removing a CSV chip preserves other files and disables commit", async ({ page }) => {
  await resetSession(page);
  await openUploadPage(page);
  await fillContext(page);
  await uploadPdf(page);
  await page.locator("#upload-csv").setInputFiles(files.csvGanjil);
  await expect(page.locator('[data-upload-chip="csv"]')).toHaveCount(1);
  await uploadExcel(page);

  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeEnabled();
  await page.getByRole("button", { name: "Hapus transaksi_ganjil.csv" }).click();

  await expect(page.locator('[data-upload-chip="csv"]')).toHaveCount(0);
  await expect(page.locator('[data-upload-chip="pdf"]')).toBeVisible();
  await expect(page.locator('[data-upload-chip="excel"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeDisabled();
});
