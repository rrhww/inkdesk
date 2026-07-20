import { expect, test } from "@playwright/test";

test("renders and reads the live Vault Markdown graph", async ({ page }, testInfo) => {
  test.setTimeout(90_000);

  await page.goto("/app/wiki");
  await expect(page.getByText("GRAPH SYNC ACTIVE", { exact: true })).toBeVisible({ timeout: 60_000 });

  const nodes = page.locator(".react-flow__node");
  const edges = page.locator(".react-flow__edge");
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
  await expect(page.getByText("GRAPH SYNC ACTIVE", { exact: true })).toBeVisible({ timeout: 60_000 });
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
  await expect(page.getByText("GRAPH SYNC ACTIVE", { exact: true })).toBeVisible({ timeout: 60_000 });

  const decisionNode = page.getByText("技术决策与约束", { exact: true });
  await decisionNode.hover();
  const activeMarker = page
    .getByTestId("rf__node-vault:wiki/tech-decisions.md")
    .locator('[data-state="active"] > span[aria-hidden="true"]');
  const focusedEdgePath = page
    .getByRole("button", { name: "Edge from vault:wiki/index.md to vault:wiki/tech-decisions.md" })
    .locator(".react-flow__edge-path");

  await expect(activeMarker).toHaveCSS("animation-name", "none");
  await expect(focusedEdgePath).toHaveCSS("animation-name", "none");
});
