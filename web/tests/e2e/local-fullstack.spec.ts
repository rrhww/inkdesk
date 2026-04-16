import { expect, test, type Browser, type Page } from "@playwright/test";

function noteCard(page: Page, title: string, actionLabel: string) {
  return page
    .getByRole("heading", { name: title, exact: true })
    .locator("xpath=ancestor::*[self::article or self::section or self::div][1]")
    .filter({
      has: page.getByRole("button", { name: actionLabel })
    });
}

function planCard(page: Page, title: string) {
  return page
    .getByRole("heading", { name: title, exact: true, level: 4 })
    .locator("xpath=ancestor::div[.//summary[normalize-space()='编辑计划']][1]");
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill("owner@inkdesk.local");
  await page.getByLabel("密码").fill("inkdesk-owner");
  await page.getByRole("button", { name: "进入主系统" }).click();
  await expect(page).toHaveURL(/\/app$/);
}

async function verifyPublicSurface(browser: Browser, publicPath: string, title: string, excerpt: string, bodySnippet: string) {
  const context = await browser.newContext();

  try {
    const page = await context.newPage();

    await page.goto("/");
    await expect(page.getByText(title).first()).toBeVisible();

    await page.goto(publicPath);
    await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(page.getByText(excerpt)).toBeVisible();
    await expect(page.getByText(bodySnippet)).toBeVisible();
  } finally {
    await context.close();
  }
}

async function verifyPublicSurfaceRemoved(browser: Browser, publicPath: string, title: string) {
  const context = await browser.newContext();

  try {
    const page = await context.newPage();

    await page.goto(publicPath);
    await expect(page.getByText("这个页面没有被公开出来")).toBeVisible();

    await page.goto("/");
    await expect(page.getByText(title)).toHaveCount(0);
  } finally {
    await context.close();
  }
}

test.describe("local full-stack loop", () => {
  test.describe.configure({ mode: "serial" });

  test.skip(
    !process.env.INKDESK_E2E_FULLSTACK,
    "请通过 `npm run e2e:fullstack` 运行，并先启动 Docker 基础设施、Spring Boot 与 Next.js 所需配置。"
  );

  test("owner can complete the local full-stack loop", async ({ browser, page }) => {
    test.setTimeout(120_000);

    const runId = Date.now().toString(36);
    const noteTitle = `fullstack-local-loop-${runId}`;
    const noteExcerpt = `Local loop excerpt ${runId}`;
    const noteBodySnippet = `This note verifies the local full-stack loop end to end ${runId}.`;
    const planTitle = `fullstack-plan-${runId}`;
    const settingsDisplayName = `Loop ${runId}`;
    const settingsTitle = `Local Loop Owner ${runId}`;
    const settingsSummary = `Local full-stack acceptance summary ${runId}.`;
    const settingsLocation = `Shanghai-${runId}`;

    await login(page);

    await page.goto("/app/notes/new");
    await page.getByPlaceholder("输入标题...").fill(noteTitle);
    await page.getByLabel("摘要").fill(noteExcerpt);
    await page.getByLabel("正文（Markdown）").fill(`# ${noteTitle}\n\n${noteBodySnippet}`);
    await page.getByRole("button", { name: "保存到主系统" }).click();

    await expect(page).toHaveURL(/\/app\/notes\/note-/);
    await expect(page.getByText("知识资产已写入主系统，刷新后会继续回显。")).toBeVisible();

    await page.goto("/app/publish");
    const draftEntry = noteCard(page, noteTitle, "发布到公开输出");
    await expect(draftEntry).toBeVisible();
    await draftEntry.getByRole("button", { name: "发布到公开输出" }).click();

    const publishedEntry = noteCard(page, noteTitle, "撤回到主系统");
    await expect(publishedEntry).toBeVisible();

    const publicPathText = await publishedEntry.getByText(/^公开路径：/).textContent();
    const publicPath = publicPathText?.replace("公开路径：", "").trim();

    if (!publicPath || !publicPath.startsWith("/articles/")) {
      throw new Error(`Unexpected public path: ${publicPathText ?? "<empty>"}`);
    }

    await verifyPublicSurface(browser, publicPath, noteTitle, noteExcerpt, noteBodySnippet);

    await publishedEntry.getByRole("button", { name: "撤回到主系统" }).click();
    await expect(noteCard(page, noteTitle, "发布到公开输出")).toBeVisible();
    await verifyPublicSurfaceRemoved(browser, publicPath, noteTitle);

    await page.goto("/app/plans");
    const createSection = page.locator("section").filter({
      has: page.getByRole("heading", { name: "把下一步动作先固定进主系统" })
    });

    await createSection.getByLabel("标题").fill(planTitle);
    await createSection.getByLabel("焦点标签").fill("本地闭环");
    await createSection.getByLabel("摘要").fill("用一条真实计划覆盖知识、发布、设置与登出链路。");
    await createSection.getByLabel("下一步动作").fill("确认全链路验收通过并收口文档。");
    await createSection.getByLabel("检索词").fill(noteTitle);
    await createSection.getByLabel("Agent 提示词").fill("围绕当前本地全栈闭环继续推进。");
    await createSection.getByLabel(noteTitle).check();
    await createSection.getByRole("button", { name: "创建计划" }).click();

    const createdPlan = planCard(page, planTitle);
    await expect(createdPlan).toBeVisible();
    await expect(createdPlan.getByRole("link", { name: noteTitle, exact: true })).toBeVisible();

    await createdPlan.locator("summary").click();
    await createdPlan.getByLabel("状态").selectOption("done");
    await createdPlan.getByLabel("下一步动作").fill("本地闭环验收已完成。");
    await createdPlan.getByRole("button", { name: "保存计划变更" }).click();
    await expect(createdPlan).toContainText("已完成");

    await page.goto("/app/settings");
    await page.getByLabel("显示名称").fill(settingsDisplayName);
    await page.getByLabel("公开标题").fill(settingsTitle);
    await page.getByLabel("公开地点").fill(settingsLocation);
    await page.getByLabel("公开摘要").fill(settingsSummary);
    await page.getByLabel("默认页").selectOption("/app/plans");

    const compactModeToggle = page.getByRole("button", { name: "紧凑模式" });
    if ((await compactModeToggle.getAttribute("aria-pressed")) !== "true") {
      await compactModeToggle.click();
    }

    await page.getByRole("button", { name: "保存设置" }).click();
    await expect(page.getByText("设置已写入主系统，刷新后会继续回显。")).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("显示名称")).toHaveValue(settingsDisplayName);
    await expect(page.getByLabel("公开标题")).toHaveValue(settingsTitle);
    await expect(page.getByLabel("公开地点")).toHaveValue(settingsLocation);
    await expect(page.getByLabel("公开摘要")).toHaveValue(settingsSummary);
    await expect(page.getByLabel("默认页")).toHaveValue("/app/plans");
    await expect(page.getByRole("button", { name: "紧凑模式" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("owner@inkdesk.local")).toBeVisible();

    await page.getByRole("button", { name: "退出主系统" }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.goto("/app/plans");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "进入主系统" })).toBeVisible();
  });
});
