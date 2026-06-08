import { expect, test } from "@playwright/test";
import { openUploadPage, resetSession } from "./upload-helpers";

test("upload page initial state is simplified", async ({ page }) => {
  await resetSession(page);
  await openUploadPage(page);

  await expect(page.getByRole("heading", { name: "Konteks Periode Data" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Periode Data Opsional" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Simpan Periode" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Simpan Sesi Upload" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeDisabled();
});
