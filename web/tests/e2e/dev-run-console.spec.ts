import { expect, test } from "@playwright/test";

const corsHeaders = {
  "access-control-allow-origin": "http://localhost:3301",
  "access-control-allow-methods": "GET,POST,OPTIONS",
  "access-control-allow-headers": "content-type",
};

test("a delayed initial list cannot erase a newly created run", async ({ page }) => {
  let releaseInitialList!: () => void;
  const initialListReleased = new Promise<void>((resolve) => {
    releaseInitialList = resolve;
  });

  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      json: {
        summary: {
          totalPages: 0,
          brokenLinkCount: 0,
          orphanPageCount: 0,
          missingFrontmatterCount: 0,
          missingSourceCount: 0,
        },
        issues: [],
      },
      headers: corsHeaders,
    });
  });

  await page.route("**/api/runs", async (route) => {
    const method = route.request().method();
    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders });
      return;
    }
    if (method === "GET") {
      await initialListReleased;
      await route.fulfill({ json: [], headers: corsHeaders });
      return;
    }
    await route.fulfill({
      status: 201,
      json: {
        id: "run-browser-race",
        workspaceId: "workspace-inkdesk",
        type: "PRD",
        title: "浏览器竞态回归",
        goal: "验证旧列表响应不会覆盖新任务",
        repoContext: null,
        status: "active",
        currentStage: "context",
        stageStatus: "pending",
        stages: [],
        events: [],
        createdAt: "2026-06-21T12:00:00Z",
        updatedAt: "2026-06-21T12:00:00Z",
      },
      headers: corsHeaders,
    });
  });

  await page.goto("/app", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /新建任务/ }).click();
  await page.getByPlaceholder("任务标题").fill("浏览器竞态回归");
  await page.getByPlaceholder("任务目标").fill("验证旧列表响应不会覆盖新任务");
  const createResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/runs") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "创建", exact: true }).click();
  await createResponse;

  const initialListResponse = page.waitForResponse(
    (response) => response.url().endsWith("/api/runs") && response.request().method() === "GET",
  );
  releaseInitialList();
  await initialListResponse;

  await expect(page.getByRole("heading", { name: "浏览器竞态回归" })).toBeVisible();
});
