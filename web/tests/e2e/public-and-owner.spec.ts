import { expect, test } from "@playwright/test";

test("public home stays public-only", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /公开输出与长期项目分享/ })).toBeVisible();
  await expect(page.getByText("公开统计")).toBeVisible();
  await expect(page.getByText("进入主系统")).toHaveCount(0);
});

test("unauthenticated access to /app redirects to /login", async ({ page }) => {
  await page.goto("/app/plans");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "进入主系统" })).toBeVisible();
});

test("owner can log in and reach the private system", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("owner@inkdesk.local");
  await page.getByLabel("密码").fill("inkdesk-owner");
  await page.getByRole("button", { name: "进入主系统" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText("快速动作")).toBeVisible();
});
