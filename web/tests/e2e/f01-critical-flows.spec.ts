import { expect, test } from "@playwright/test";

test.describe("F01 critical browser flows", () => {
  test.describe.configure({ mode: "serial" });

  test.skip(
    !process.env.INKDESK_E2E_FULLSTACK,
    "请通过 `npm run e2e:fullstack` 运行 F01 浏览器基线。"
  );

  test.beforeEach(async ({ request }) => {
    const status = await request.get("/api/vault/status");
    expect(status.ok()).toBeTruthy();
    if (!(await status.json()).vaultType) {
      const initialized = await request.post("/api/vault/initialize", { data: { vaultType: "general" } });
      expect(initialized.ok()).toBeTruthy();
    }
  });

  test("keeps the public operations home available without a login redirect", async ({ page }) => {
    await page.goto("/app");

    await expect(page).toHaveURL("/app");
    await expect(page.getByText(/Dev Run|研发任务|创建任务/).first()).toBeVisible();
  });

  test("keeps a newly created Dev Run when an old list response arrives late", async ({ page }) => {
    test.setTimeout(45_000);
    let releaseStaleList: (() => void) | undefined;
    const staleList = new Promise<void>((resolve) => {
      releaseStaleList = resolve;
    });
    let delayedInitialList = false;

    await page.route("**/api/runs", async (route) => {
      if (route.request().method() === "GET" && !delayedInitialList) {
        delayedInitialList = true;
        await staleList;
        await route.fulfill({ contentType: "application/json", body: "[]" });
        return;
      }
      await route.continue();
    });

    await page.goto("/app");
    await page.getByRole("button", { name: "新建任务" }).click();
    await page.getByPlaceholder("任务标题").fill("F01 延迟列表保护");
    await page.getByPlaceholder("任务目标").fill("确认旧列表不能覆盖刚创建的任务。");
    await page.getByRole("button", { name: "创建", exact: true }).click();
    await expect(page.getByText("F01 延迟列表保护")).toBeVisible();

    releaseStaleList?.();
    await expect(page.getByText("F01 延迟列表保护")).toBeVisible();
  });

  test("shows the six-stage Run track and exposes invalid transitions", async ({ page, request }) => {
    test.setTimeout(45_000);
    const created = await request.post("/api/runs", {
      data: {
        type: "PRD",
        title: "F01 阶段轨道",
        goal: "验证阶段轨道和非法转换。",
        repoContext: "inkdesk"
      }
    });
    expect(created.status()).toBe(201);
    const run = await created.json();
    const invalid = await request.post(`/api/runs/${run.id}/advance`, { data: { action: "approve" } });
    expect(invalid.status()).toBe(409);

    await page.goto(`/app/runs/${run.id}`);
    await expect(page.getByText("阶段轨道", { exact: true })).toBeVisible();
    for (const label of ["上下文", "方案", "审阅", "编码", "测试", "沉淀"]) {
      await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
    }
  });

  test("keeps Source, Review, Topic, Ask, and Deposit on the review-first path", async ({ page, request }) => {
    test.setTimeout(60_000);
    const source = await request.post("/api/raw", {
      data: {
        kind: "TEXT",
        title: "F01 知识链路来源",
        excerpt: "F01 通过 Review-first 固定恢复前的知识写入边界。",
        body: "Synthetic F01 browser evidence for the source, review, topic, ask, and deposit path."
      }
    });
    expect(source.status()).toBe(201);
    const sourceRecord = await source.json();

    const reviews = await request.get("/api/ingest");
    expect(reviews.ok()).toBeTruthy();
    const review = (await reviews.json()).find((item: { sourceId: string }) => item.sourceId === sourceRecord.id);
    expect(review).toBeTruthy();

    const accepted = await request.post(`/api/ingest/${review.id}/accept`);
    expect(accepted.ok()).toBeTruthy();
    const { topicId } = await accepted.json();

    await page.goto(`/app/wiki/${topicId}`);
    await expect(page.getByText("Current Understanding", { exact: true })).toBeVisible();

    const asked = await request.post("/api/ask", {
      data: { topicId, question: "F01 的知识写入边界是什么？", mode: "vault" }
    });
    expect(asked.ok()).toBeTruthy();
    const ask = await asked.json();

    const deposited = await request.post("/api/deposits", {
      data: {
        source: "answer",
        askTurnId: ask.id,
        payload: { title: "F01 浏览器沉淀", understanding: "这项沉淀仍需经过 Review。" }
      }
    });
    expect(deposited.status()).toBe(201);
    const deposit = await deposited.json();

    const pendingReviews = await request.get("/api/ingest");
    expect((await pendingReviews.json()).some((item: { id: string; status: string }) => item.id === deposit.reviewId && item.status === "PENDING")).toBeTruthy();
  });

  test("keeps operational pages accessible and renders a not-found state", async ({ page, request }) => {
    test.setTimeout(60_000);
    const endpoints = ["/api/raw", "/api/ingest", "/api/wiki", "/api/compile/queue", "/api/health", "/api/skills"];
    for (const endpoint of endpoints) {
      expect((await request.get(endpoint)).ok()).toBeTruthy();
    }

    for (const route of ["/app/raw", "/app/ingest", "/app/wiki", "/app/ask", "/app/compile", "/app/health", "/app/skills"]) {
      await page.goto(route);
      await expect(page).toHaveURL(route);
      await expect(page.locator("main").first()).toBeVisible();
      await expect(page.locator("body")).not.toContainText("/login");
    }

    await page.goto("/app/wiki/f01-resource-that-does-not-exist");
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator("main").first()).toBeVisible();
  });
});
