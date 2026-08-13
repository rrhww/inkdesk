import { rm, writeFile } from "node:fs/promises";
import path from "node:path";

import { expect, test } from "@playwright/test";

test("starts with a six-stage research flow and drills into a readable document cluster", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ DOCUMENTS$/)).toBeVisible({ timeout: 60_000 });

  await expect(page.locator(".react-flow__node-hierarchy")).toHaveCount(6);
  await expect(page.getByTestId("rf__node-stage:requirements").getByText("需求定义", { exact: true })).toBeVisible();
  await expect(page.getByTestId("rf__node-stage:design").getByText("方案设计", { exact: true })).toBeVisible();
  await expect(page.getByTestId("rf__node-stage:verification").getByText("验证审计", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Research flow" })).toHaveAttribute("aria-pressed", "true");

  const navigator = page.getByTestId("desktop-navigator");
  await navigator.getByRole("button", { name: /方案设计/ }).click();
  await expect(page.getByRole("navigation", { name: "Graph breadcrumb" })).toContainText("方案设计");
  await expect(page.locator(".react-flow__node-hierarchy").count()).resolves.toBeGreaterThan(0);

  await navigator.getByRole("button", { name: /Architecture/ }).click();
  await expect(page.getByRole("navigation", { name: "Graph breadcrumb" })).toContainText("Architecture");
  await expect.poll(() => page.locator(".react-flow__node").count()).toBeLessThanOrEqual(30);
  await expect(
    page.getByTestId("rf__node-vault:wiki/tech-decisions.md").getByText("技术决策与约束", { exact: true })
  ).toBeVisible();

  await navigator.getByRole("button", { name: /技术决策与约束/ }).click();
  const reader = page.getByRole("dialog");
  await expect(reader.getByText("wiki/tech-decisions.md", { exact: true })).toBeVisible();
  await expect(reader.getByText(/AI 不能直接写 wiki/)).toBeVisible();
  await expect(page).toHaveURL(/stage=design/);
  await expect(page).toHaveURL(/domain=architecture/);
  await expect(page).toHaveURL(/node=vault%3Awiki%2Ftech-decisions.md/);
  await page.screenshot({ path: testInfo.outputPath("wiki-hierarchy-document.png"), fullPage: true });

  await page.reload();
  await expect(reader.getByText(/AI 不能直接写 wiki/)).toBeVisible({ timeout: 60_000 });
});

test("search navigates to the classified document instead of centering an invisible global node", async ({ page }) => {
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ DOCUMENTS$/)).toBeVisible({ timeout: 60_000 });

  const search = page.getByRole("combobox", { name: "Search graph nodes" });
  await page.keyboard.press("Control+k");
  await expect(search).toBeFocused();
  await search.fill("技术决策与约束");
  await expect(page.getByRole("option", { name: /技术决策与约束/ })).toBeVisible();
  await page.keyboard.press("Enter");

  await expect(page.getByRole("dialog").getByText(/AI 不能直接写 wiki/)).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Graph breadcrumb" })).toContainText("方案设计");
  await expect(page.getByRole("navigation", { name: "Graph breadcrumb" })).toContainText("Architecture");
  await expect(page.getByTestId("rf__node-vault:wiki/tech-decisions.md").locator('[data-state="active"]')).toBeVisible();
});

test("keeps the full graph available only through the advanced raw view", async ({ page }, testInfo) => {
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ DOCUMENTS$/)).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".react-flow__node")).toHaveCount(6);

  await page.getByText("ADVANCED", { exact: true }).click();
  await page.getByRole("button", { name: "Raw graph" }).click();
  await expect(page.getByRole("button", { name: "Raw graph" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => page.locator(".react-flow__node").count()).toBeGreaterThan(30);
  await expect(page).toHaveURL(/view=raw/);
  await page.screenshot({ path: testInfo.outputPath("wiki-raw-graph-advanced.png"), fullPage: true });
});

test("uses list-first hierarchy navigation on a narrow viewport", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ DOCUMENTS$/)).toBeVisible({ timeout: 60_000 });

  await expect(page.locator(".react-flow")).toBeHidden();
  const navigator = page.getByTestId("mobile-navigator");
  await expect(navigator).toBeVisible();
  await navigator.getByRole("button", { name: /方案设计/ }).click();
  await navigator.getByRole("button", { name: /Architecture/ }).click();
  await navigator.getByRole("button", { name: /技术决策与约束/ }).click();

  const reader = page.getByRole("dialog");
  await expect(reader).toHaveCSS("width", "390px");
  await expect(reader.getByText(/AI 不能直接写 wiki/)).toBeVisible();
  await expect.poll(async () => reader.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return { left: Math.round(bounds.left), right: Math.round(bounds.right) };
  })).toEqual({ left: 0, right: 390 });
  const horizontalOverflow = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const offenders = [...document.querySelectorAll<HTMLElement>("body *")]
      .map((element) => {
        const bounds = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          testId: element.dataset.testid ?? "",
          className: typeof element.className === "string" ? element.className : "",
          left: Math.round(bounds.left),
          right: Math.round(bounds.right)
        };
      })
      .filter((element) => element.left < -1 || element.right > viewportWidth + 1)
      .slice(0, 10);
    return {
      viewportWidth,
      scrollWidth: document.documentElement.scrollWidth,
      offenders
    };
  });
  expect(horizontalOverflow).toEqual({ viewportWidth: 390, scrollWidth: 390, offenders: [] });
  await page.screenshot({ path: testInfo.outputPath("wiki-hierarchy-mobile.png"), fullPage: true });
});

test("keeps Watchdog, search, Mermaid, and pulse glow working for a new classified document", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const probePath = path.resolve(process.cwd(), "..", "server", "vault", "wiki", "hierarchy-live-probe.md");

  await rm(probePath, { force: true });
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ DOCUMENTS$/)).toBeVisible({ timeout: 60_000 });

  try {
    await writeFile(
      probePath,
      "---\ntitle: Hierarchy Live Probe\ntype: concept\nstage: knowledge\ndomain: general\ncategory: concept\nimportance: core\ngraphVisibility: primary\nstatus: transient\n---\n# Hierarchy Live Probe\n\nWatcher integration probe.\n\n```mermaid\ngraph TD\n  Stage --> Domain --> Document\n```\n",
      "utf8"
    );

    const search = page.getByRole("combobox", { name: "Search graph nodes" });
    await search.fill("Hierarchy Live Probe");
    await expect(page.getByRole("option", { name: /Hierarchy Live Probe/ })).toBeVisible({ timeout: 30_000 });
    await page.keyboard.press("Enter");

    const probeNode = page.getByTestId("rf__node-vault:wiki/hierarchy-live-probe.md");
    await expect(probeNode.locator('[data-state="active"]')).toBeVisible();
    const reader = page.getByRole("dialog");
    await expect(reader.getByRole("img", { name: "Mermaid architecture diagram" }).locator("svg")).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: testInfo.outputPath("wiki-hierarchy-live-probe.png"), fullPage: true });
  } finally {
    await rm(probePath, { force: true });
  }

  await expect(page.getByText("Hierarchy Live Probe", { exact: true })).toHaveCount(0, { timeout: 30_000 });
});

test("disables graph focus motion when reduced motion is requested", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/app/wiki?stage=design&domain=architecture");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ DOCUMENTS$/)).toBeVisible({ timeout: 60_000 });

  const search = page.getByRole("combobox", { name: "Search graph nodes" });
  await search.fill("技术决策与约束");
  await page.keyboard.press("Enter");
  const activeMarker = page.getByTestId("rf__node-vault:wiki/tech-decisions.md").locator('[data-state="active"] > span[aria-hidden="true"]');
  await expect(activeMarker).toHaveCSS("animation-name", "none");
});
