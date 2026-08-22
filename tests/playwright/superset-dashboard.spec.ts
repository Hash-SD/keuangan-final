import { expect, test } from "@playwright/test";

const DASHBOARD_URL = process.env.SUPERSET_DASHBOARD_URL || "http://localhost:8092/";

test.use({ viewport: { width: 1920, height: 1080 } });
test.describe.configure({ mode: "serial" });

test("superset mirror dashboard renders a centered analytics layout at 1920px", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto(DASHBOARD_URL);

  await expect(page.locator("html[data-ui-version='2026-08-22-redesign']")).toHaveCount(1);
  await expect(page.locator("#sourceInline .pill")).toHaveCount(0);

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
    .toBe(4);

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
  expect(shellMaxWidth).toBe("1480px");
  const shellWidth = await shell.evaluate((el) => Math.round(el.getBoundingClientRect().width));
  expect(shellWidth).toBeLessThanOrEqual(1480);

  const grid = page.locator("#dashboardGrid");
  const gridWidth = await grid.evaluate((el) => Math.round(el.getBoundingClientRect().width));
  const gridCols = await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
  const colWidths = gridCols.split(" ").filter(Boolean).map((v) => parseFloat(v));
  expect(colWidths).toHaveLength(12);
  expect(Math.max(...colWidths) - Math.min(...colWidths)).toBeLessThanOrEqual(1);
  expect(gridWidth).toBeGreaterThan(1200);

  const treemapCard = page.locator("#dashboardGrid .chart-card--feature");
  await expect(treemapCard).toHaveCount(1);
  expect(await treemapCard.evaluate((el) => getComputedStyle(el).gridColumn)).toBe("1 / -1");

  const treemapSpacing = await treemapCard.evaluate((card) => {
    const heading = card.querySelector(".card-heading")?.getBoundingClientRect();
    const title = card.querySelector(".card-heading h2")?.getBoundingClientRect();
    const subtitle = card.querySelector(".card-heading p")?.getBoundingClientRect();
    const chart = card.querySelector(".chart-treemap")?.getBoundingClientRect();
    const cardRect = card.getBoundingClientRect();
    return {
      headingToChart: heading && chart ? Math.round(chart.top - heading.bottom) : -1,
      titleToSubtitle: title && subtitle ? Math.round(subtitle.top - title.bottom) : -1,
      chartToCardBottom: chart ? Math.round(cardRect.bottom - chart.bottom) : -1,
      chartHeight: chart ? Math.round(chart.height) : -1,
    };
  });
  expect(treemapSpacing.headingToChart).toBeLessThanOrEqual(8);
  expect(treemapSpacing.titleToSubtitle).toBeLessThanOrEqual(2);
  expect(treemapSpacing.chartToCardBottom).toBeLessThanOrEqual(18);
  expect(treemapSpacing.chartHeight).toBeLessThanOrEqual(360);

  const metricTexts = await page.locator("#kpiGrid .metric-card").allTextContents();
  const itemMetric = metricTexts.find((text) => /Jumlah Item/i.test(text));
  expect(itemMetric).toBeDefined();
  expect(itemMetric).not.toMatch(/Rp\s?/i);
  const primaryKpi = page.locator("#kpiGrid .metric-card--primary");
  await expect(primaryKpi).toHaveCount(1);
  expect(
    await primaryKpi.evaluate((element) => getComputedStyle(element, "::before").content),
  ).toBe("none");
  expect(
    await primaryKpi.evaluate((element) => getComputedStyle(element).backgroundImage),
  ).toBe("none");
  expect(
    await page.locator("#kpiGrid .metric-label").first().evaluate((element) => getComputedStyle(element).textTransform),
  ).toBe("none");

  const chartTitles = await page.locator("#dashboardGrid h2").allTextContents();
  expect(chartTitles.every((title) => !/^\s*SILARAS\s*\|/i.test(title))).toBe(true);

  const tableHeaders = await page.locator("#dashboardGrid th").allTextContents();
  expect(tableHeaders.every((header) => !header.includes("_"))).toBe(true);
  expect(tableHeaders.every((header) => header === header.trim())).toBe(true);
  expect(tableHeaders).toEqual(
    expect.arrayContaining(["Uraian detail", "Harga satuan", "Sumber data", "Total detail", "Total rekap"]),
  );
  await expect(page.locator(".page-size").first()).toContainText("Baris");

  const detailHeaders = await page
    .locator("#dashboardGrid .table-card")
    .filter({ hasText: "Detail item biaya" })
    .locator("th")
    .allTextContents();
  expect(detailHeaders).toContain("Sumber data");

  const detailTable = page.locator("#dashboardGrid .table-card").filter({ hasText: "Detail item biaya" });
  const detailRow = detailTable.locator("tbody tr").first();
  await expect(detailRow).toBeVisible();
  const detailValues = await detailRow.evaluate((row) => {
    const headers = [...(row.parentElement?.parentElement?.querySelectorAll("thead th") || [])]
      .map((header) => header.textContent?.trim() || "");
    const values = [...row.children].map((cell) => cell.textContent?.trim() || "");
    return {
      quantity: values[headers.indexOf("Kuantitas")],
      unitPrice: values[headers.indexOf("Harga satuan")],
      amount: values[headers.indexOf("Jumlah")],
    };
  });
  expect(detailValues.quantity).toBe("1");
  expect(detailValues.unitPrice).toBe(detailValues.amount);
  expect(detailValues.amount).toMatch(/Rp\s?\d{1,3}(\.\d{3})+/);

  const validationTable = page.locator("#dashboardGrid .table-card").filter({ hasText: "Validasi rekap" });
  await expect(validationTable).toHaveCount(1);
  const validationSelisih = await validationTable.locator("tbody tr").evaluateAll((rows) => {
    const headers = [...(rows[0]?.parentElement?.parentElement?.querySelectorAll("thead th") || [])]
      .map((header) => header.textContent?.trim() || "");
    const index = headers.indexOf("Selisih");
    return rows.map((row) => row.children[index]?.textContent?.trim() || "");
  });
  expect(validationSelisih.length).toBeGreaterThan(0);
  expect(validationSelisih.every((value) => !/Rp\s?/i.test(value))).toBe(true);

  const yearlySummary = page
    .locator("#dashboardGrid .table-card")
    .filter({ hasText: "Ringkasan per Tahun" });
  const itemCounts = await yearlySummary.locator("tbody tr").evaluateAll((rows) =>
    rows.map((row) => row.children[2]?.textContent?.trim() || ""),
  );
  expect(itemCounts.length).toBeGreaterThan(0);
  expect(itemCounts.every((value) => !/Rp\s?/i.test(value))).toBe(true);

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

test("chart and table selections cross-filter the complete dashboard", async ({ page }) => {
  const filterRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/chart/") && request.url().includes("filters=")) filterRequests.push(request.url());
  });

  await page.goto(DASHBOARD_URL);
  await expect
    .poll(() => page.locator("#footerStatus").textContent())
    .toContain("Semua data berhasil dimuat");

  const yearlyChart = page.locator("#dashboardGrid .chart-card").filter({ hasText: "Anggaran per tahun" }).locator(".chart");
  await expect(yearlyChart).toBeVisible();
  await expect(yearlyChart.locator("canvas")).toBeVisible();
  await expect.poll(() => yearlyChart.evaluate((element) => Boolean((window as any).echarts.getInstanceByDom(element)))).toBe(true);
  await yearlyChart.scrollIntoViewIfNeeded();
  const point = await yearlyChart.evaluate((element) => {
    const chart = (window as any).echarts.getInstanceByDom(element);
    const option = chart.getOption();
    const category = String(option.xAxis[0].data[0]);
    const value = Number(option.series[0].data[0].value ?? option.series[0].data[0]);
    const pixel = chart.convertToPixel({ xAxisIndex: 0, yAxisIndex: 0 }, [category, value / 2]);
    const rect = element.getBoundingClientRect();
    return { x: rect.left + pixel[0], y: rect.top + pixel[1], category };
  });
  await page.mouse.click(point.x, point.y);

  await expect(page.locator(".cross-filter-chip")).toContainText(point.category);
  await expect
    .poll(() => page.locator("#activeFilters").textContent())
    .toContain("Tahun");
  await expect.poll(() => filterRequests.length).toBeGreaterThan(0);

  const clear = page.locator("#clearCrossFilters");
  await expect(clear).toBeVisible();
  await clear.click();
  await expect(page.locator(".cross-filter-chip")).toHaveCount(0);
});

test("superset mirror dashboard stays compact and scroll-safe on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(DASHBOARD_URL);

  await expect
    .poll(() => page.locator("#footerStatus").textContent())
    .toContain("Semua data berhasil dimuat");

  const layout = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    analyticsColumns: getComputedStyle(document.querySelector("#dashboardGrid") as Element).gridTemplateColumns,
    chartColumns: [...document.querySelectorAll("#dashboardGrid .chart-card:not(.span-2)")].map(
      (element) => getComputedStyle(element).gridColumn,
    ),
    primaryWidth: Math.round(document.querySelector(".metric-card--primary")?.getBoundingClientRect().width || 0),
    shellWidth: Math.round(document.querySelector(".dashboard-shell")?.getBoundingClientRect().width || 0),
  }));

  expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth + 1);
  expect(layout.analyticsColumns.trim().split(/\s+/)).toHaveLength(1);
  expect(layout.chartColumns.length).toBeGreaterThanOrEqual(2);
  expect(layout.chartColumns.every((column) => column === "1 / -1")).toBe(true);
  expect(layout.primaryWidth).toBeLessThanOrEqual(layout.shellWidth);
});
