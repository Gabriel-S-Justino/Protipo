// Browser regression checks. Fixtures are served only by Playwright, never by the application.
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE || "playwright");
const fs = require("node:fs");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.TEST_BROWSER_EXECUTABLE || chromium.executablePath(),
    args: [
      "--use-gl=angle",
      "--use-angle=swiftshader",
      "--enable-unsafe-swiftshader",
    ],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  const warnings = [];
  page.on("console", (m) => {
    if (m.type() === "warning" && m.text().includes("MapLibre"))
      warnings.push(m.text());
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const regions = [
    {
      id: 76,
      name: "Brasil",
      level: "country",
      geocode: "BR",
      bbox_w: -74,
      bbox_s: -34,
      bbox_e: -28,
      bbox_n: 6,
    },
    {
      id: 23,
      name: "Ceará",
      level: "state",
      geocode: "23",
      bbox_w: -42.7,
      bbox_s: -7.6,
      bbox_e: -37.2,
      bbox_n: -2.2,
    },
  ];
  const cell = (period) => ({
    cell_id: 1,
    cell_key: "-79:-10",
    lat: -4.75,
    lon: -39.25,
    state: "Ceará",
    period_of_year: period,
    probability: 0.65,
    ci_low: 0.4,
    ci_high: 0.83,
    years_used: 10,
    expected_count: 100,
    confidence: "medium",
    validation: { brier_score: 0.19, test_years: 7, method: "rolling_origin" },
    calculated_at: "2026-11-06",
  });
  const features = [
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [-39.25, -4.75] },
      properties: { ...cell(1), weight: 100 },
    },
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [-49.75, -10.25] },
      properties: {
        ...cell(1),
        cell_id: 2,
        state: "Tocantins",
        lat: -10.25,
        lon: -49.75,
        probability: 0.35,
        weight: 300,
      },
    },
  ];
  let fail = false;
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body;
    if (fail)
      return route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Dados indisponíveis: teste de erro" }),
      });
    if (url.pathname === "/api/regions") body = regions;
    else if (url.pathname === "/api/calendar/probability")
      body = Array.from(
        { length: url.searchParams.get("period_type") === "month" ? 12 : 53 },
        (_, i) => cell(i + 1),
      );
    else if (
      url.pathname === "/api/calendar/locations" ||
      url.pathname === "/api/map/heat"
    )
      body = { type: "FeatureCollection", features };
    else if (url.pathname === "/api/dashboard/summary")
      body = {
        total: 500,
        last_30d: 100,
        last_30d_avg_hist: 5,
        unified_series_note: "Série unificada de teste.",
        unit: "atividade VIIRS equivalente",
      };
    else if (url.pathname === "/api/metadata/coverage")
      body = {
        period_start: "2012-01-01",
        period_end: "2026-11-05",
        covered_days: 5000,
        instruments: ["VIIRS"],
        harmonized_share: 0.3,
      };
    else if (url.pathname === "/api/series/unified")
      body = {
        unit: "atividade equivalente",
        region: "Brasil",
        provenance: "MODIS harmonizado",
        points: [
          {
            period_start: "2026-01-01",
            value_viirs: 100,
            coverage_fraction: 1,
            quality: "ok",
          },
        ],
      };
    else body = [];
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  fs.mkdirSync(".test-artifacts", { recursive: true });
  for (const [path, label] of [
    ["/map", "flat"],
    ["/globe", "globe"],
    ["/map3d", "terrain"],
  ]) {
    await page.goto("http://127.0.0.1:4173" + path);
    await page.locator(".maplibregl-canvas").waitFor();
    await page
      .getByText("Carregando mapa…", { exact: true })
      .waitFor({ state: "hidden", timeout: 30000 });
    await page.waitForTimeout(2500);
    assert.equal(await page.locator(".maplibregl-canvas").count(), 1);
    assert.equal(
      await page
        .getByText("Falha ao carregar as camadas do mapa.", { exact: false })
        .count(),
      0,
    );
    await page.screenshot({
      path: ".test-artifacts/" + label + ".png",
      fullPage: true,
    });
  }
  await page
    .getByRole("combobox", { name: "Área de análise" })
    .selectOption("23");
  await page
    .getByRole("heading", { name: "Calor no território · Ceará" })
    .waitFor();
  await page.getByRole("button", { name: "Plano", exact: true }).click();
  await page.getByRole("button", { name: "Globo", exact: true }).click();
  await page.getByRole("button", { name: "Relevo 3D", exact: true }).click();
  await page.waitForTimeout(2000);
  assert.equal(
    await page.locator(".maplibregl-canvas").count(),
    1,
    "map lifecycle cleanup",
  );
  await page.goto("http://127.0.0.1:4173/calendar");
  await page
    .getByRole("table", { name: "Calendário de recorrência por área" })
    .waitFor();
  assert.equal(await page.getByRole("columnheader").count(), 54);
  await page
    .getByRole("combobox", { name: "Agrupar calendário" })
    .selectOption("month");
  await page.waitForTimeout(1500);
  assert.equal(await page.getByRole("columnheader").count(), 13);
  await page
    .getByRole("button", { name: "Ceará, mês 8:", exact: false })
    .click();
  assert.equal(
    await page
      .getByRole("combobox", { name: "Período do calendário" })
      .inputValue(),
    "8",
  );
  await page.getByText("Área selecionada", { exact: true }).waitFor();
  await page.screenshot({
    path: ".test-artifacts/calendar.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.waitForTimeout(1500);
  assert.equal(
    await page
      .locator("body")
      .evaluate((el) => el.scrollWidth <= window.innerWidth),
    true,
    "mobile page overflow",
  );
  await page.screenshot({ path: ".test-artifacts/mobile.png", fullPage: true });
  fail = true;
  await page.goto("http://127.0.0.1:4173/map");
  await page
    .getByRole("alert")
    .filter({ hasText: "Dados indisponíveis: teste de erro" })
    .waitFor({ timeout: 20000 });
  assert.deepEqual(errors, []);
  assert.deepEqual(
    warnings,
    [],
    "map layers must render without worker or source errors",
  );
  console.log(
    JSON.stringify({
      status: "passed",
      checks: [
        "3 map modes",
        "mode switching and cleanup",
        "state filter",
        "53 weekly/12 monthly columns",
        "period and location selection",
        "mobile layout",
        "API error state",
      ],
      pageErrors: errors,
      mapWarnings: warnings,
    }),
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
