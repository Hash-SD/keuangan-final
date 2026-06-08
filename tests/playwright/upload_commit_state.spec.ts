import { expect, test } from "@playwright/test";
import { fillContext, openUploadPage, resetSession, uploadCsv, uploadExcel, uploadPdf } from "./upload-helpers";

test("commit writes Raw Layer state without claiming ETL success", async ({ page }) => {
  await resetSession(page);
  await openUploadPage(page);
  await fillContext(page);
  await uploadPdf(page);
  await uploadCsv(page);
  await uploadExcel(page);

  await page.getByRole("button", { name: "Unggah ke Data Lakehouse" }).click();
  await expect
    .poll(async () => {
      const response = await page.request.get("http://localhost:8091/api/upload/session/status");
      const payload = await response.json();
      return payload.status;
    })
    .toBe("committed");

  await expect(page.getByText("Dataset aktif sudah tersedia di Raw Layer. Quality Gate belum dijalankan.")).toBeVisible();
  await expect(page.getByText("ETL berhasil")).toHaveCount(0);
  await expect(page.getByText("Gold ready", { exact: true })).toHaveCount(0);
  await expect(page.getByText(/Session ID: .*Quality Gate belum dijalankan/)).toBeVisible();
});
