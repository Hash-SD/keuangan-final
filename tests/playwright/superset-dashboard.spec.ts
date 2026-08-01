import { expect, test } from "@playwright/test";

const DASHBOARD_URL = "http://localhost:8092/";

test.use({ viewport: { width: 1920, height: 1080 } });

test("superset mirror dashboard renders full-width in two fluid columns at 1920px", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto(DASHBOARD_URL);

  await expect(
    page.getByRole("heading", { name: /Dashboard Anggaran IKU Sains Data/ }),
  ).toBeVisible();

  const kpis = page.locator("#kpiGrid .metric-card");
  await expect(kpis.first()).toBeVisible();
  await expect
    .poll(() => page.locator("#footerStatus").textContent())
    .toContain("Semua data berhasil dimuat");

  await expect
    .poll(() => kpis.count())
    .toBeGreaterThanOrEqual(1);

  const kpiValues = page.locator("#kpiGrid .metric-value");
  await expect
    .poll(async () => (await kpiValues.allTextContents()).some((t) => !t.includes("Memuat")))
    .toBe(true);

  const chartCards = page.locator("#dashboardGrid .chart-card:not(.span-2)");
  const count = await chartCards.count();
  expect(count).toBeGreaterThanOrEqual(2);

  const boxes = await chartCards.evaluateAll((els) =>
    els.map((el) => {
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width) };
    }),
  );

  const first = boxes[0];
  const second = boxes[1];
  expect(Math.abs(first.x - second.x)).toBeGreaterThan(50);

  const secondRow = boxes.find((b) => b.y > first.y + 40);
  expect(secondRow).toBeTruthy();
  expect(Math.abs((secondRow as { x: number }).x - first.x)).toBeLessThanOrEqual(2);

  const shell = page.locator(".dashboard-shell");
  const shellMaxWidth = await shell.evaluate((el) => getComputedStyle(el).maxWidth);
  expect(shellMaxWidth).toBe("none");

  const grid = page.locator("#dashboardGrid");
  const gridWidth = await grid.evaluate((el) => Math.round(el.getBoundingClientRect().width));
  const gridCols = await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
  const colWidths = gridCols.split(" ").filter(Boolean).map((v) => parseFloat(v));
  expect(colWidths).toHaveLength(2);
  expect(Math.abs(colWidths[0] - colWidths[1])).toBeLessThanOrEqual(1);
  expect(Math.abs(colWidths[0] * 2 + 20 - gridWidth)).toBeLessThanOrEqual(4);

  await expect(page.locator("#dashboardGrid canvas").first()).toBeVisible();

  const headingOffsets = await page
    .locator("#dashboardGrid .card-heading")
    .evaluateAll((els) =>
      els.map((el) => {
        const heading = el.getBoundingClientRect();
        const h2 = el.querySelector("h2");
        return h2 ? Math.round(h2.getBoundingClientRect().x - heading.x) : -1;
      }),
    );
  expect(headingOffsets.length).toBeGreaterThanOrEqual(5);
  for (const offset of headingOffsets) {
    expect(offset).toBeGreaterThanOrEqual(40);
    expect(offset).toBeLessThanOrEqual(60);
  }

  expect(consoleErrors).toEqual([]);
});
