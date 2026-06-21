import { expect, test, type Page } from "@playwright/test";

test.describe("local full-stack loop (no auth)", () => {
  test.describe.configure({ mode: "serial" });

  test.skip(
    !process.env.INKDESK_E2E_FULLSTACK,
    "请通过 `npm run e2e:fullstack` 运行，并先启动 Docker 基础设施、Python 主后端与 Next.js 所需配置。"
  );

  test("home page is Dev Run Console (no login required)", async ({ page }) => {
    test.setTimeout(30_000);

    await page.goto("/app");
    await expect(page).toHaveURL(/\/app$/);
    await expect(page.getByText(/Dev Run|研发任务|创建任务/).first()).toBeVisible();
  });

  test("can navigate to compile and health pages without redirect to login", async ({ page }) => {
    test.setTimeout(30_000);

    await page.goto("/app/compile");
    await expect(page).toHaveURL("/app/compile");
    await expect(page.getByRole("heading", { name: "编译流水线" })).toBeVisible();

    await page.goto("/app/health");
    await expect(page).toHaveURL("/app/health");
    await expect(page.getByRole("heading", { name: "知识库健康" })).toBeVisible();
  });

  test("resource not found shows 404 without redirect", async ({ page }) => {
    test.setTimeout(30_000);

    await page.goto("/app/wiki/nonexistent-404-test");
    // should show a 404 or not-found page, NOT redirect to /login
    await expect(page.locator("body")).not.toContainText("Inkdesk 研发控制台");
  });

  test("Dev Run full loop: create run → Ask → deposit → approve → complete", async ({ page, request }) => {
    test.setTimeout(120_000);

    // 1. 创建 Dev Run
    const createResp = await request.post("/api/runs", {
      data: {
        type: "PRD",
        title: "E2E 全链路测试",
        goal: "验证创建 Run → Ask 追问 → deposit → 审阅 → approve 推进 → complete 的完整闭环",
        repoContext: "inkdesk",
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const run = await createResp.json();
    const runId: string = run.id;
    expect(runId).toBeTruthy();

    // 2. 在 Dev Run 上下文中发起 Ask
    const askResp = await request.post("/api/ask", {
      data: {
        question: "Inkdesk 的产品定位是什么？",
        mode: "vault",
        runId,
      },
    });
    expect(askResp.ok()).toBeTruthy();
    const ask = await askResp.json();
    const askTurnId: string = ask.id;
    expect(askTurnId).toBeTruthy();

    // 3. Ask 回答 Deposit
    const depositResp = await request.post("/api/deposits", {
      data: {
        source: "answer",
        runId,
        askTurnId,
        payload: { title: "E2E 测试沉淀", understanding: ask.answer.slice(0, 200) },
      },
    });
    expect(depositResp.ok()).toBeTruthy();
    const deposit = await depositResp.json();
    expect(deposit.reviewId).toBeTruthy();

    // 4. 前端打开任务详情页并检查阶段轨道
    await page.goto(`/app/runs/${runId}`);
    await expect(page.getByText("E2E 全链路测试")).toBeVisible();
    await expect(page.getByText("阶段轨道")).toBeVisible();

    // 5. 通过 API 推进所有阶段 → 完成
    const stages = ["context", "solution", "review", "coding", "testing", "deposit"];
    for (const stage of stages) {
      await request.post(`/api/runs/${runId}/events`, {
        data: { stage, eventType: "stage_output", payload: { summary: `${stage} done` } },
      });
      if (stage !== "deposit") {
        const adv = await request.post(`/api/runs/${runId}/advance`, { data: { action: "approve" } });
        expect(adv.ok()).toBeTruthy();
      }
    }
    // complete
    const completeResp = await request.post(`/api/runs/${runId}/advance`, { data: { action: "complete" } });
    expect(completeResp.ok()).toBeTruthy();
    const completed = await completeResp.json();
    expect(completed.status).toBe("completed");
    expect(completed.completedAt).toBeTruthy();

    // 6. 页面刷新后应显示已完成
    await page.reload();
    await expect(page.getByText(/完成于/)).toBeVisible();
  });

  test("illegal state transitions are rejected", async ({ request }) => {
    test.setTimeout(30_000);

    const createResp = await request.post("/api/runs", {
      data: {
        type: "REFACTOR",
        title: "状态机边界测试",
        goal: "验证非法状态转换被拒绝",
        repoContext: "inkdesk",
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const run = await createResp.json();

    // 刚创建不能 approve（stage_status == "pending"）
    const badApprove = await request.post(`/api/runs/${run.id}/advance`, { data: { action: "approve" } });
    expect(badApprove.status()).toBe(409);

    // 不能从未知 ID 访问
    const missing = await request.get("/api/runs/nonexistent-run-id");
    expect(missing.status()).toBe(404);

    // 非空 runId 不能访问跨资源
    const cross = await request.get(`/api/runs/nonexistent-run-id/events`);
    expect(cross.status()).toBe(404);
  });
});
