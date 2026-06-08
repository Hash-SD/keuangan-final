import { expect, test } from "@playwright/test";
import { fillContext, openUploadPage, resetSession, uploadCsv, uploadExcel, uploadPdf } from "./upload-helpers";

test("PDF, CSV, and Excel remain visible while readiness changes", async ({ page }) => {
  await resetSession(page);
  await openUploadPage(page);
  await fillContext(page);

  await uploadPdf(page);
  await expect(page.locator('[data-upload-chip="pdf"]')).toBeVisible();
  await expect(page.locator('[data-remove-upload="pdf"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeDisabled();

  await uploadCsv(page);
  await expect(page.locator('[data-upload-chip="pdf"]')).toBeVisible();
  await expect(page.locator('[data-upload-chip="csv"]')).toHaveCount(2);
  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeDisabled();

  await uploadExcel(page);
  await expect(page.locator('[data-upload-chip="pdf"]')).toBeVisible();
  await expect(page.locator('[data-upload-chip="csv"]')).toHaveCount(2);
  await expect(page.locator('[data-upload-chip="excel"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeEnabled();
});
