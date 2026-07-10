import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const webRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const previewRoot = join(webRoot, 'preview-dev-run-console');
const readPreview = (relativePath) => {
  const path = join(previewRoot, relativePath);
  return existsSync(path) ? readFileSync(path, 'utf8') : '';
};

const requiredFiles = [
  'index.html',
  'styles.css',
  'app.js',
  'assets/traework/colors_and_type.css',
  'assets/traework/components.css',
];

const requiredIcons = [
  'add.svg',
  'ViewLeft_line.svg',
  'task.svg',
  'Run.svg',
  'DocumentFeedback.svg',
  'chat-ai.svg',
  'document.svg',
  'File.svg',
  'ai_stars.svg',
  'code.svg',
  'warning_simple.svg',
  'Search.svg',
  'settings.svg',
  'Close.svg',
  'Down.svg',
  'list-filter.svg',
  'more-action.svg',
  'Link.svg',
  'success_simple.svg',
  'information_simple.svg',
];

test('prototype contains the required local files', () => {
  for (const relativePath of [...requiredFiles, ...requiredIcons.map((name) => `assets/traework/icons/${name}`)]) {
    assert.equal(existsSync(join(previewRoot, relativePath)), true, `missing ${relativePath}`);
  }
});

test('prototype exposes exactly eight primary views', () => {
  const html = readPreview('index.html');
  const views = [...html.matchAll(/data-view="([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(views, ['overview', 'run', 'review', 'ask', 'sources', 'wiki', 'skills', 'evaluation']);
});

test('navigation preserves the approved grouped information architecture', () => {
  const html = readPreview('index.html');
  for (const label of ['工作流', '上下文', '自动化', '系统']) {
    assert.match(html, new RegExp(`data-nav-group="${label}"`));
  }
  for (const label of ['总览', 'Dev Runs', '审阅队列', 'Context Ask', 'Sources', 'Wiki', 'Skills', 'Evaluations', 'Health', 'Settings']) {
    assert.match(html, new RegExp(`>${label}<`));
  }
  assert.doesNotMatch(html, /data-nav[^>]*>\s*Compile\s*</i);
});

test('prototype consumes only local TraeWork critical resources', () => {
  const html = readPreview('index.html');
  assert.match(html, /assets\/traework\/colors_and_type\.css/);
  assert.match(html, /assets\/traework\/components\.css/);
  assert.doesNotMatch(html, /https?:\/\//i);
  assert.doesNotMatch(html, /material-symbols|material icons/i);
  assert.doesNotMatch(html, /<svg[\s>]/i);
});

test('prototype declares a local TraeWork favicon', () => {
  const html = readPreview('index.html');
  assert.match(html, /<link rel="icon" href="assets\/traework\/icons\/[^"]+\.svg">/);
});

test('prototype keeps brand emphasis to the New Dev Run action', () => {
  const html = readPreview('index.html');
  const brandButtons = html.match(/ds-btn--brand/g) ?? [];
  assert.equal(brandButtons.length, 1);
  assert.match(html, /class="[^"]*ds-btn--brand[^"]*"[^>]*>[\s\S]*?新建 Dev Run[\s\S]*?<\/button>/);
});

test('prototype includes keyboard and screen-reader anchors', () => {
  const html = readPreview('index.html');
  assert.match(html, /class="skip-link"[^>]*href="#main-content"/);
  assert.match(html, /id="main-content"[^>]*tabindex="-1"/);
  assert.match(html, /id="mobile-drawer"[^>]*aria-hidden="true"/);
  assert.match(html, /id="new-run-dialog"[^>]*aria-modal="true"/);
  assert.match(html, /id="live-region"[^>]*aria-live="polite"/);
});

test('page-local styles remain token-first and light-only', () => {
  const css = readPreview('styles.css');
  assert.doesNotMatch(css, /#[0-9a-f]{3,8}\b/i);
  assert.doesNotMatch(css, /prefers-color-scheme|dark-mode|data-theme=["']dark/i);
  assert.match(css, /var\(--bg-base-default\)/);
  assert.match(css, /var\(--spacer-32\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
});

test('every page-local CSS variable resolves to the TraeWork snapshot or local stylesheet', () => {
  const localCss = readPreview('styles.css');
  const allCss = `${readPreview('assets/traework/colors_and_type.css')}\n${readPreview('assets/traework/components.css')}\n${localCss}`;
  const references = new Set([...localCss.matchAll(/var\((--[a-z0-9-]+)/gi)].map((match) => match[1]));
  const definitions = new Set([...allCss.matchAll(/(--[a-z0-9-]+)\s*:/gi)].map((match) => match[1]));
  const missing = [...references].filter((name) => !definitions.has(name));
  assert.deepEqual(missing, []);
});

test('interaction script covers navigation, dialogs, filters, and detail switching', () => {
  const script = readPreview('app.js');
  for (const behavior of ['activateView', 'openDialog', 'closeDialog', 'applyReviewFilter', 'selectDetail', 'toggleDrawer']) {
    assert.match(script, new RegExp(`function ${behavior}\\b`), `missing ${behavior}`);
  }
});
