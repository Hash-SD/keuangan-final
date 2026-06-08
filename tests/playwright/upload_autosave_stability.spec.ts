import { expect, test } from "@playwright/test";
import { openUploadPage, resetSession } from "./upload-helpers";

test("autosave keeps scroll position and focused field value stable", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await resetSession(page);
  await openUploadPage(page);
  await page.evaluate(() => window.scrollTo(0, 520));
  const before = await page.evaluate(() => window.scrollY);

  const academicYear = page.locator("#ctx-target-tahun-akademik");
  await academicYear.fill("2026/2027");
  await expect(page.locator("#contextAutosaveStatus")).toContainText("Tersimpan sementara", { timeout: 5000 });

  const after = await page.evaluate(() => window.scrollY);
  expect(after).toBeGreaterThanOrEqual(before - 20);
  await expect(academicYear).toHaveValue("2026/2027");
  expect(errors).toEqual([]);
});

test("background polling does not replace an actively edited field", async ({ page }) => {
  await resetSession(page);
  await openUploadPage(page);
  const academicYear = page.locator("#ctx-target-tahun-akademik");

  await academicYear.focus();
  await academicYear.fill("2030/2031");
  await page.waitForTimeout(31000);

  await expect(academicYear).toBeFocused();
  await expect(academicYear).toHaveValue("2030/2031");
});
