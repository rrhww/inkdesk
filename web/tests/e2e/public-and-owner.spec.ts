import { expect, test } from "@playwright/test";

test("root entry now redirects into the private LLM Wiki login", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "进入私有 LLM Wiki" })).toBeVisible();
});

test("unauthenticated access to /app redirects to /login", async ({ page }) => {
  await page.goto("/app/wiki");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "进入私有 LLM Wiki" })).toBeVisible();
});

test("owner can log in and reach the private system", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("owner@inkvault.local");
  await page.getByLabel("密码").fill("inkvault-owner");
  await page.getByRole("button", { name: "进入工作区" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText("Today Vault Panel", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "知识库", exact: true })).toBeVisible();
  await expect(page.getByText("设置")).toHaveCount(0);
});
