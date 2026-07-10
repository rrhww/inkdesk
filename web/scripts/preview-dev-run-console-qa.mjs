import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:4177';
const webRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const outputDir = join(webRoot, 'preview-dev-run-console', 'qa');
const browserPath = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].find(existsSync);

async function assertNoPageOverflow(page, width) {
  const metrics = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  assert.ok(metrics.documentWidth <= width + 1, JSON.stringify(metrics));
  assert.ok(metrics.bodyWidth <= width + 1, JSON.stringify(metrics));
}

async function assertAssetsLoaded(page) {
  const broken = await page.locator('img').evaluateAll((images) => images
    .filter((image) => !image.complete || image.naturalWidth === 0)
    .map((image) => image.getAttribute('src')));
  assert.deepEqual(broken, [], `broken images: ${broken.join(', ')}`);
}

async function assertView(page, name) {
  const view = page.locator(`[data-view="${name}"]`);
  assert.equal(await view.count(), 1);
  assert.equal(await view.isVisible(), true, `view ${name} is not visible`);
}

function attachDiagnostics(page) {
  const diagnostics = { consoleErrors: [], pageErrors: [], failedRequests: [], httpErrors: [] };
  page.on('console', (message) => {
    if (message.type() === 'error') {
      const location = message.location();
      diagnostics.consoleErrors.push(`${message.text()} @ ${location.url || 'unknown'}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.pageErrors.push(String(error)));
  page.on('requestfailed', (request) => {
    diagnostics.failedRequests.push(`${request.url()}: ${request.failure()?.errorText ?? 'unknown'}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400) diagnostics.httpErrors.push(`${response.status()} ${response.url()}`);
  });
  return diagnostics;
}

function assertDiagnosticsClean(diagnostics) {
  assert.deepEqual(diagnostics.httpErrors, []);
  assert.deepEqual(diagnostics.consoleErrors, []);
  assert.deepEqual(diagnostics.pageErrors, []);
  assert.deepEqual(diagnostics.failedRequests, []);
}

async function runViewportCheck(browser, width, height, route, screenshotName) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  const diagnostics = attachDiagnostics(page);

  await page.goto(`${baseUrl}/#${route}`, { waitUntil: 'networkidle' });
  await assertView(page, route);
  assert.equal(await page.locator('[data-view]').count(), 8);
  await assertAssetsLoaded(page);
  await assertNoPageOverflow(page, width);
  await page.screenshot({ path: join(outputDir, screenshotName), fullPage: true });
  assertDiagnosticsClean(diagnostics);
  await context.close();
}

async function runDesktopFlow(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  const diagnostics = attachDiagnostics(page);
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  await page.locator('.nav-item[data-route="run"]').click();
  await assertView(page, 'run');
  await page.getByRole('button', { name: /Test.*等待/ }).click();
  assert.equal(await page.locator('[data-stage-panel="test"]').isVisible(), true);
  await page.getByRole('button', { name: /Coding.*执行中/ }).click();
  const event = page.locator('[data-event-toggle]').first();
  await event.click();
  assert.equal(await event.getAttribute('aria-expanded'), 'true');

  await page.locator('.nav-item[data-route="review"]').click();
  await assertView(page, 'review');
  await page.getByRole('button', { name: /知识沉淀.*1/ }).click();
  assert.equal(await page.locator('[data-detail-panel="review-wiki"]').isVisible(), true);
  await page.getByRole('button', { name: /高风险.*1/ }).click();
  assert.equal(await page.locator('[data-detail-panel="review-solution"]').isVisible(), true);

  await page.locator('.nav-item[data-route="ask"]').click();
  await assertView(page, 'ask');
  const citation = page.locator('[data-citation-toggle]').first();
  await citation.click();
  assert.equal(await citation.getAttribute('aria-expanded'), 'true');
  await page.locator('[data-deposit-proposal]').click();
  assert.equal(await page.locator('[data-deposit-proposal]').isDisabled(), true);

  await page.locator('.nav-item[data-route="sources"]').click();
  await assertView(page, 'sources');
  await page.locator('[data-detail-target="source-article"]').click();
  assert.equal(await page.locator('[data-detail-panel="source-article"]').isVisible(), true);

  await page.locator('.nav-item[data-route="wiki"]').click();
  await assertView(page, 'wiki');
  await page.locator('[data-detail-target="wiki-context"]').click();
  assert.equal(await page.locator('[data-detail-panel="wiki-context"]').isVisible(), true);

  await page.locator('.nav-item[data-route="skills"]').click();
  await assertView(page, 'skills');
  await page.locator('[data-detail-target="skill-review"]').click();
  assert.equal(await page.locator('[data-detail-panel="skill-review"]').isVisible(), true);

  await page.locator('.nav-item[data-route="evaluation"]').click();
  await assertView(page, 'evaluation');
  await page.locator('[data-detail-target="eval-router"]').click();
  assert.equal(await page.locator('[data-detail-panel="eval-router"]').isVisible(), true);

  await page.getByRole('button', { name: '新建 Dev Run' }).click();
  const dialog = page.locator('#new-run-dialog');
  assert.equal(await dialog.isVisible(), true);
  const submit = page.getByRole('button', { name: '创建并开始 Context' });
  await submit.click();
  assert.equal(await page.locator('#run-name-error').textContent(), '请输入任务名称。');
  await page.locator('#run-name').fill('验证静态原型交互');
  await page.locator('#run-goal').fill('验证导航、门禁、响应式与本地资源加载。');
  await submit.click();
  assert.equal(await dialog.isHidden(), true);
  await assertView(page, 'run');
  assert.match(await page.locator('#live-region').textContent(), /验证静态原型交互/);

  await assertAssetsLoaded(page);
  await assertNoPageOverflow(page, 1440);
  await page.screenshot({ path: join(outputDir, 'desktop-flow-final.png'), fullPage: true });
  assertDiagnosticsClean(diagnostics);
  await context.close();
}

async function runMobileDrawerFlow(browser) {
  const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  const openButton = page.getByRole('button', { name: '打开导航' });
  await openButton.focus();
  await openButton.click();
  const drawer = page.locator('#mobile-drawer');
  assert.equal(await drawer.getAttribute('aria-hidden'), 'false');
  assert.equal(await page.locator('.nav-item[data-route="review"]').isVisible(), true);
  await page.locator('.nav-item[data-route="review"]').click();
  await assertView(page, 'review');
  assert.equal(await drawer.getAttribute('aria-hidden'), 'true');
  await assertNoPageOverflow(page, 375);

  await openButton.click();
  await page.keyboard.press('Escape');
  assert.equal(await drawer.getAttribute('aria-hidden'), 'true');
  assert.equal(await page.evaluate(() => document.activeElement === document.querySelector('[data-drawer-open]')), true);
  await context.close();
}

async function runReducedMotionCheck(browser) {
  const context = await browser.newContext({
    viewport: { width: 1024, height: 768 },
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  const duration = await page.locator('.app-view.is-active').evaluate(
    (element) => getComputedStyle(element).animationDuration,
  );
  assert.ok(['0.001s', '0s'].includes(duration), duration);
  await context.close();
}

mkdirSync(outputDir, { recursive: true });
assert.ok(browserPath, 'Chrome or Edge is required for local preview QA');
const browser = await chromium.launch({ headless: true, executablePath: browserPath });
try {
  await runViewportCheck(browser, 375, 812, 'overview', 'overview-375.png');
  await runViewportCheck(browser, 768, 900, 'ask', 'ask-768.png');
  await runViewportCheck(browser, 1024, 800, 'run', 'run-1024.png');
  await runViewportCheck(browser, 1440, 960, 'review', 'review-1440.png');
  await runDesktopFlow(browser);
  await runMobileDrawerFlow(browser);
  await runReducedMotionCheck(browser);
} finally {
  await browser.close();
}

console.log('Preview QA passed for 375, 768, 1024, and 1440 viewports.');
