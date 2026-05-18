import { expect, test, type Page } from "@playwright/test";

async function loginAsOwner(page: Page) {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("owner@inkvault.local");
  await page.getByLabel("密码").fill("inkvault-owner");
  await page.getByRole("button", { name: "进入工作区" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

function healthSignal(page: Page) {
  return page
    .getByText(/Ask 最近发现 \d+ 个知识缺口/)
    .or(page.getByText(/wiki 里还有 \d+ 个开放问题/))
    .or(page.getByText(/ingest 队列有 \d+ 条待审阅提案/))
    .or(page.getByText(/raw 里有 \d+ 条材料等待编译/))
    .first();
}

test("private entry, owner login, and ask-first workspace stay connected", async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "进入私有 LLM Wiki" })).toBeVisible();

  await page.goto("/app/wiki");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "进入私有 LLM Wiki" })).toBeVisible();

  await loginAsOwner(page);
  await expect(page.getByRole("heading", { name: "问答" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "判断面板" })).toBeVisible();
  await expect(page.getByText("建议提问", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "问答", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "知识库", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "健康", exact: true })).toHaveCount(0);
  await expect(page.getByText("设置")).toHaveCount(0);
  await expect(healthSignal(page)).toBeVisible();

  await page.goto("/app/ask");
  await expect(page).toHaveURL(/\/app\/ask$/);
  await expect(page.getByRole("heading", { name: "问答" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "判断面板" })).toBeVisible();
  await expect(healthSignal(page)).toBeVisible();

  await page.goto("/app/topics");
  await expect(page).toHaveURL(/\/app\/topics$/);
  await expect(page.getByRole("heading", { name: "这条 wiki 路径当前不存在" })).toBeVisible();
  await expect(page.getByRole("link", { name: "回到 Ask-first 工作区" })).toHaveAttribute("href", "/app");
});
