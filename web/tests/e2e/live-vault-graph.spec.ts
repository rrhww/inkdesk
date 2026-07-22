import { rm, writeFile } from "node:fs/promises";
import path from "node:path";

import { expect, test } from "@playwright/test";

test("renders and reads the live Vault Markdown graph", async ({ page }, testInfo) => {
  test.setTimeout(90_000);

  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });

  const nodes = page.locator(".react-flow__node");
  const edges = page.locator(".react-flow__edge");
  await expect.poll(() => nodes.count()).toBeGreaterThan(5);
  await expect(page.getByRole("button", { name: "All nodes" })).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: "Repository nodes" }).click();
  await expect(page.getByRole("button", { name: "Repository nodes" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => nodes.count()).toBeGreaterThan(5);
  await expect(page.getByText("技术决策与约束", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "Vault nodes" }).click();
  await expect(page.getByRole("button", { name: "Vault nodes" })).toHaveAttribute("aria-pressed", "true");
  await expect(nodes).toHaveCount(5);
  await expect(edges).toHaveCount(4);
  await expect(page.locator(".react-flow__edge-straight")).toHaveCount(4);
  await expect(page.locator(".react-flow__node-concept")).toHaveCount(1);
  await expect(page.locator(".react-flow__node-action")).toHaveCount(4);
  await expect(page.getByText("技术决策与约束", { exact: true })).toBeVisible();
  await expect(page.getByText("系统架构与技术栈", { exact: true })).toBeVisible();

  const decisionNode = page.getByText("技术决策与约束", { exact: true });
  await decisionNode.hover();
  const decisionNodeRoot = page.getByTestId("rf__node-vault:wiki/tech-decisions.md");
  const architectureNodeRoot = page.getByTestId("rf__node-vault:wiki/system-architecture.md");
  const rootNode = page.getByTestId("rf__node-vault:wiki/index.md");
  const focusedEdge = page.getByRole("button", {
    name: "Edge from vault:wiki/index.md to vault:wiki/tech-decisions.md"
  });
  const dimmedEdge = page.getByRole("button", {
    name: "Edge from vault:wiki/index.md to vault:wiki/system-architecture.md"
  });
  await expect(decisionNodeRoot.locator('[data-state="active"]')).toBeVisible();
  await expect(decisionNodeRoot).toHaveCSS("opacity", "1");
  await expect(rootNode).toHaveCSS("opacity", "1");
  await expect(architectureNodeRoot).toHaveCSS("opacity", "0.25");
  await expect(focusedEdge).toHaveClass(/animated/);
  await expect(focusedEdge.locator(".react-flow__edge-path")).toHaveCSS("stroke", "rgb(5, 150, 105)");
  await expect(dimmedEdge.locator(".react-flow__edge-path")).toHaveCSS("opacity", "0.12");
  for (const handle of await decisionNodeRoot.locator(".react-flow__handle").all()) {
    await expect(handle).toHaveCSS("opacity", "0");
  }
  await page.screenshot({ path: testInfo.outputPath("wiki-live-vault-hover.png"), fullPage: true });

  await page.locator("main").hover({ position: { x: 420, y: 120 } });
  await expect(architectureNodeRoot).toHaveCSS("opacity", "1");
  await expect(focusedEdge).not.toHaveClass(/animated/);
  await expect(dimmedEdge.locator(".react-flow__edge-path")).toHaveCSS("opacity", "1");

  await decisionNodeRoot.focus();
  await page.keyboard.press("Enter");
  const reader = page.locator("aside");
  await expect(reader.getByText("wiki/tech-decisions.md", { exact: true })).toBeVisible();
  await expect(architectureNodeRoot).toHaveCSS("opacity", "0.25");
  await expect(reader.getByText(/AI 不能直接写 wiki/)).toBeVisible();
  await expect(reader.getByText("type: concept", { exact: true })).toHaveCount(0);
  await expect(reader.locator("article.markdown-viewer")).toBeVisible();

  await page.screenshot({ path: testInfo.outputPath("wiki-live-vault.png"), fullPage: true });

  await page.getByRole("button", { name: "关闭阅读器" }).click();
  await page.getByRole("button", { name: "知识库目录", exact: true }).click();
  await expect(reader.getByText("wiki/index.md", { exact: true })).toBeVisible();
  await expect(reader.locator("pre")).toBeVisible();
  await expect(reader.locator("pre")).toHaveCSS("background-color", "rgb(15, 23, 42)");
  await expect(reader.locator("pre code")).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await reader.locator("pre").scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("wiki-live-vault-code.png"), fullPage: true });
});

test("keeps the live graph and reader usable on a narrow viewport", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });
  await expect.poll(() => page.locator(".react-flow__node").count()).toBeGreaterThan(5);

  const search = page.getByRole("combobox", { name: "Search graph nodes" });
  const scope = page.getByRole("group", { name: "Graph scope" });
  await expect(search).toBeVisible();
  await expect(scope).toBeVisible();
  await expect.poll(async () => (await search.boundingBox())?.y).toBeGreaterThanOrEqual(80);
  await expect.poll(async () => {
    const searchBox = await search.boundingBox();
    const scopeBox = await scope.boundingBox();
    return searchBox && scopeBox ? scopeBox.y - (searchBox.y + searchBox.height) : -1;
  }).toBeGreaterThanOrEqual(20);
  await page.screenshot({ path: testInfo.outputPath("wiki-live-vault-mobile-search.png"), fullPage: true });

  await page.getByRole("button", { name: "Vault nodes" }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(5);
  await page.getByText("技术决策与约束", { exact: true }).click();
  const reader = page.locator("aside");
  await expect(reader).toHaveCSS("width", "390px");
  await expect(reader.getByText(/AI 不能直接写 wiki/)).toBeVisible();
  await expect(page.getByTestId("rf__node-vault:wiki/system-architecture.md")).toHaveCSS("opacity", "0.25");
  await expect.poll(async () => (await reader.boundingBox())?.x).toBe(0);
  await page.screenshot({ path: testInfo.outputPath("wiki-live-vault-mobile.png"), fullPage: true });
});

test("disables graph focus motion when reduced motion is requested", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });

  const search = page.getByRole("combobox", { name: "Search graph nodes" });
  await search.fill("技术决策与约束");
  await page.keyboard.press("Enter");
  const activeMarker = page
    .getByTestId("rf__node-vault:wiki/tech-decisions.md")
    .locator('[data-state="active"] > span[aria-hidden="true"]');
  const focusedEdgePath = page
    .getByRole("button", { name: "Edge from vault:wiki/index.md to vault:wiki/tech-decisions.md" })
    .locator(".react-flow__edge-path");

  await expect(activeMarker).toHaveCSS("animation-name", "none");
  await expect(focusedEdgePath).toHaveCSS("animation-name", "none");
});

test("locates graph nodes and renders Mermaid from live Vault Markdown", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const probePath = path.resolve(process.cwd(), "..", "server", "vault", "wiki", "mermaid-live-probe.md");

  await rm(probePath, { force: true });
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });

  const search = page.getByRole("combobox", { name: "Search graph nodes" });
  await page.keyboard.press("Control+k");
  await expect(search).toBeFocused();
  await search.fill("技术决策与约束");
  await expect(page.getByRole("option", { name: /技术决策与约束/ })).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(search).toHaveValue("");
  await expect(
    page.getByTestId("rf__node-vault:wiki/tech-decisions.md").locator('[data-state="active"]')
  ).toBeVisible();

  try {
    await writeFile(
      probePath,
      "---\ntitle: Mermaid Live Probe\ntype: concept\nstatus: transient\n---\n# Mermaid Live Probe\n\nWatcher integration probe.\n\n```mermaid\ngraph TD\n  Vault --> Reader\n```\n",
      "utf8"
    );

    const probeNode = page.getByText("Mermaid Live Probe", { exact: true });
    await expect(probeNode).toBeVisible({ timeout: 30_000 });
    await search.fill("Mermaid Live Probe");
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("rf__node-vault:wiki/mermaid-live-probe.md").locator('[data-state="active"]')).toBeVisible();
    await probeNode.click();

    const reader = page.locator("aside");
    const diagram = reader.getByRole("img", { name: "Mermaid architecture diagram" });
    await expect(diagram.locator("svg")).toBeVisible({ timeout: 30_000 });
    await expect(diagram).toHaveCSS("border-top-left-radius", "0px");
    await page.screenshot({ path: testInfo.outputPath("wiki-search-mermaid.png"), fullPage: true });
  } finally {
    await rm(probePath, { force: true });
  }

  await expect(page.getByText("Mermaid Live Probe", { exact: true })).toHaveCount(0, { timeout: 30_000 });
});

test("applies Watchdog graph updates without reloading the page", async ({ page }) => {
  test.setTimeout(90_000);
  const probePath = path.resolve(process.cwd(), "..", "server", "vault", "wiki", "sse-live-probe.md");

  await rm(probePath, { force: true });
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });
  const nodes = page.locator(".react-flow__node");
  const baselineNodeCount = await nodes.count();
  expect(baselineNodeCount).toBeGreaterThan(5);

  try {
    await writeFile(
      probePath,
      "---\ntitle: SSE Live Probe\ntype: concept\nstatus: transient\n---\n# SSE Live Probe\n\nWatcher integration probe.\n",
      "utf8"
    );

    const probeNode = page.getByText("SSE Live Probe", { exact: true });
    await expect(probeNode).toBeVisible({ timeout: 30_000 });
    await expect(nodes).toHaveCount(baselineNodeCount + 1);
    await expect(page.getByTestId("rf__node-vault:wiki/sse-live-probe.md").locator('[data-state="active"]')).toBeVisible();
  } finally {
    await rm(probePath, { force: true });
  }

  await expect(page.getByText("SSE Live Probe", { exact: true })).toHaveCount(0, { timeout: 30_000 });
  await expect(nodes).toHaveCount(baselineNodeCount);
});

test("groups code nodes and reduces graph noise through view modes and semantic zoom", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await page.goto("/app/wiki");
  await expect(page.getByText(/^GRAPH SYNC ACTIVE \/ \d+ NODES$/)).toBeVisible({ timeout: 60_000 });

  const viewControl = page.getByRole("group", { name: "Graph view" });
  const global = page.getByRole("button", { name: "Global graph" });
  const task = page.getByRole("button", { name: "Task focus graph" });
  const macro = page.getByRole("button", { name: "Macro graph" });
  const moduleNodes = page.locator(".react-flow__node-module");
  const graphNodes = page.locator(".react-flow__node");

  await expect(viewControl).toBeVisible();
  await expect(global).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => moduleNodes.count()).toBeGreaterThan(0);
  const globalNodeCount = await graphNodes.count();

  await macro.click();
  await expect(macro).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => graphNodes.count()).toBeLessThan(globalNodeCount);
  await expect.poll(() => page.locator(".react-flow__edge").count()).toBeGreaterThan(0);
  await page.screenshot({ path: testInfo.outputPath("wiki-macro-graph.png"), fullPage: true });

  await task.click();
  await expect(task).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => page.locator(".react-flow__node").count()).toBeGreaterThan(0);

  await global.click();
  await expect(graphNodes).toHaveCount(globalNodeCount);
  for (let index = 0; index < 10; index += 1) {
    await page.locator(".react-flow__controls-zoomin").click();
  }
  await expect.poll(() => page.locator(".react-flow__edge").count()).toBeGreaterThan(0);
  await page.locator(".react-flow__controls-fitview").click();
  await expect(page.locator(".react-flow__edge")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("wiki-semantic-zoom.png"), fullPage: true });
});
