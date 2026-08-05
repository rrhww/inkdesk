import { expect, test } from "@playwright/test";

test.describe("knowledge board", () => {
  test("redirects the app root to the Wiki dashboard", async ({ page }) => {
    for (const route of ["/", "/app"]) {
      await page.goto(route);

      await expect(page).toHaveURL(/\/app\/wiki$/);
      await expect(page.getByRole("heading", { name: "Inkdesk 知识看板" })).toBeVisible();
      await expect(page.getByText("项目知识主题")).toBeVisible();
      await expect(page.getByRole("searchbox", { name: "搜索知识主题" })).toBeVisible();
    }
  });

  test("opens a read-only Wiki node detail", async ({ page }) => {
    await page.goto("/app/wiki");
    await page.getByRole("link", { name: /打开 .*主题简报/ }).first().click();

    await expect(page).toHaveURL(/\/app\/wiki\/topic-/);
    await expect(page.getByText("当前理解", { exact: true })).toBeVisible();
    await expect(page.getByText("关键决策", { exact: true })).toBeVisible();
    await expect(page.getByText("来源与相关资料", { exact: true })).toBeVisible();
  });

  test("keeps the dashboard inside a small mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/app/wiki");

    await expect(page.getByRole("heading", { name: "Inkdesk 知识看板" })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
  });

  test("removed workbench routes render the compact not-found state", async ({ page }) => {
    const removedRoutes = [
      "/app/ask",
      "/app/compile",
      "/app/health",
      "/app/ingest",
      "/app/raw",
      "/app/runs/legacy",
      "/app/skills",
    ];

    for (const route of removedRoutes) {
      await page.goto(route);
      await expect(page.getByRole("heading", { name: "这个页面当前不存在" })).toBeVisible();
    }
  });
});
