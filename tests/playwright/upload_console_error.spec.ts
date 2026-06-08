import { expect, test } from "@playwright/test";
import { fillContext, openUploadPage, resetSession, uploadCsv, uploadExcel, uploadPdf } from "./upload-helpers";

test("upload flow does not emit browser console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await resetSession(page);
  await openUploadPage(page);
  await fillContext(page);
  await uploadPdf(page);
  await uploadCsv(page);
  await uploadExcel(page);
  await expect(page.getByRole("button", { name: "Unggah ke Data Lakehouse" })).toBeEnabled();

  expect(errors).toEqual([]);
});
