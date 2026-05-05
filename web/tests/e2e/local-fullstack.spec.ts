import { expect, test, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("owner@inkvault.local");
  await page.getByLabel("密码").fill("inkvault-owner");
  await page.getByRole("button", { name: "进入工作区" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

test.describe("local full-stack loop", () => {
  test.describe.configure({ mode: "serial" });

  test.skip(
    !process.env.INKVAULT_E2E_FULLSTACK,
    "请通过 `npm run e2e:fullstack` 运行，并先启动 Docker 基础设施、Python 主后端与 Next.js 所需配置。"
  );

  test("owner can complete the vault-first private LLM Wiki loop", async ({ page }) => {
    test.setTimeout(120_000);

    await login(page);

    await expect(page.getByText("Today Vault Panel", { exact: true })).toBeVisible();
    await expect(page.getByText("ingest 队列")).toBeVisible();
    await expect(page.getByText("最新 raw")).toBeVisible();

    await page.goto("/app/ingest");
    await expect(page.getByRole("heading", { name: "AI 编译提案队列" })).toBeVisible();
    await page.getByRole("button", { name: "接受写入 wiki" }).first().click();

    await page.goto("/app/wiki");
    await expect(page.getByRole("heading", { name: "沉淀后的知识页面" })).toBeVisible();
    await expect(page.getByRole("link", { name: "打开 wiki" }).first()).toBeVisible();
    await page.getByRole("link", { name: "打开 wiki" }).first().click();

    await expect(page.getByText("Current Understanding")).toBeVisible();
    await expect(page.getByText("Key Claims")).toBeVisible();
    await expect(page.getByText("Research Thread")).toBeVisible();

    await page.goto("/app/ask");
    await expect(page.getByRole("heading", { name: "研究问答" })).toBeVisible();
    await page.locator('a[href*="/app/ask?q="]').first().click();
    await expect(page.getByText("引用来源")).toBeVisible();
    await page.getByRole("link", { name: /继续追问/i }).first().click();
    await expect(page.getByText("正在延续上一轮问答")).toBeVisible();
    await page.getByRole("button", { name: "沉淀到 wiki" }).click();
    await expect(page).toHaveURL(/\/app\/ingest\?created=/);
    await expect(page.getByText("已从 Ask 当前回答生成一条新的 ingest 提案")).toBeVisible();

    await page.goto("/app/raw");
    await expect(page.getByRole("heading", { name: "原始材料 vault" })).toBeVisible();
    await expect(page.getByText("legacy://note-001")).toBeVisible();

    await page.getByRole("button", { name: "退出 wiki" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.goto("/app/wiki");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "进入私有 LLM Wiki" })).toBeVisible();
  });
});
