import { expect, test, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("owner@inkdesk.local");
  await page.getByLabel("密码").fill("inkdesk-owner");
  await page.getByRole("button", { name: "进入工作区" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

function healthSignal(page: Page) {
  return page
    .getByText(/wiki 里还有 \d+ 个开放问题/)
    .or(page.getByText(/ingest 队列有 \d+ 条待审阅提案/))
    .or(page.getByText(/raw 里有 \d+ 条材料等待编译/))
    .first();
}

test.describe("local full-stack loop", () => {
  test.describe.configure({ mode: "serial" });

  test.skip(
    !process.env.INKDESK_E2E_FULLSTACK,
    "请通过 `npm run e2e:fullstack` 运行，并先启动 Docker 基础设施、Python 主后端与 Next.js 所需配置。"
  );

  test("owner can complete the Dev Run-first full loop", async ({ page }) => {
    test.setTimeout(120_000);

    await login(page);

    await expect(page.getByRole("heading", { name: "研究问答" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "判断面板" })).toBeVisible();
    await expect(page.getByText("建议提问", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "问答", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "健康", exact: true })).toHaveCount(0);
    await expect(healthSignal(page)).toBeVisible();

    await page.goto("/app/ingest");
    await expect(page.getByRole("heading", { name: "AI 编译提案队列" })).toBeVisible();
    await expect(page.getByRole("button", { name: "接受写入 wiki" }).first()).toBeVisible();
    await page.getByRole("button", { name: "接受写入 wiki" }).first().click();

    await page.goto("/app");
    await expect(healthSignal(page)).toBeVisible();

    await page.goto("/app/ask");
    await expect(healthSignal(page)).toBeVisible();

    await page.goto("/app/wiki");
    await expect(page.getByRole("heading", { name: "沉淀后的知识页面" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "将 Inkdesk 重定位为私有研究型 LLM Wiki" })).toBeVisible();
    await page
      .getByRole("heading", { name: "将 Inkdesk 重定位为私有研究型 LLM Wiki" })
      .locator("..")
      .getByRole("link", { name: "打开 wiki" })
      .click();

    await expect(page.getByText("Current Understanding", { exact: true })).toBeVisible();
    await expect(page.getByText("Key Claims", { exact: true })).toBeVisible();
    await expect(page.getByText("Research Thread", { exact: true })).toBeVisible();
    await expect(page.getByText(/supported/i).first()).toBeVisible();
    await expect(page.getByText(/最近验证/).first()).toBeVisible();
    await expect(page.getByText(/最近使用/).first()).toBeVisible();
    await expect(page.getByText(/证据 1 条/).first()).toBeVisible();
    await expect(page.getByText(/最近验证 \d{4}-\d{2}-\d{2}/).first()).toBeVisible();
    await expect(page.getByText(/把产品中心收回到 raw \/ ingest \/ wiki/).first()).toBeVisible();

    await page.goto("/app/ask");
    await expect(page.getByRole("heading", { name: "研究问答" })).toBeVisible();
    await page.locator('a[href*="/app/ask?q="], a[href*="/app?q="]').first().click();
    await expect(page.getByText("引用来源")).toBeVisible();
    await expect(healthSignal(page)).toBeVisible();
    await page.locator('a[href*="continueFromAskTurnId="]').first().click();
    await expect(page.getByText("正在延续上一轮问答")).toBeVisible();
    await page.getByRole("button", { name: "沉淀到 wiki" }).click();
    await expect(page).toHaveURL(/\/app\/ingest\?created=/);
    await expect(page.getByText("已从 Ask 当前回答生成一条新的 ingest 提案")).toBeVisible();

    await page.goto("/app/raw");
    await expect(page.getByRole("heading", { name: "原始材料 vault" })).toBeVisible();
    await expect(page.getByText(/legacy-note:\/\/note-001/)).toBeVisible();

    await page.getByRole("button", { name: "退出" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.goto("/app/wiki");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Inkdesk 研发控制台" })).toBeVisible();
  });
});
