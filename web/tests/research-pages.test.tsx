import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

test("heavy workbench routes and components are physically removed", () => {
  const removedPaths = [
    "app/app/ask/page.tsx",
    "app/app/compile/page.tsx",
    "app/app/compile/[id]/page.tsx",
    "app/app/health/page.tsx",
    "app/app/ingest/page.tsx",
    "app/app/raw/page.tsx",
    "app/app/runs/[id]/page.tsx",
    "app/app/skills/page.tsx",
    "app/app/skills/[id]/page.tsx",
    "components/app-chrome.tsx",
    "components/app-header.tsx",
    "components/app-sidebar.tsx",
    "components/shell",
    "components/workbench/dev-run-console.tsx",
    "components/workbench/ask-workspace.tsx",
    "components/workbench/ask-answer-panel.tsx",
    "components/workbench/ask-answer-card.tsx",
    "components/workbench/page-shell.tsx",
    "components/workbench/raw-import-panel.tsx",
    "components/workbench/review-card.tsx",
    "components/workbench/selection-deposit.tsx",
    "components/workbench/source-card.tsx",
    "components/workbench/stages",
    "components/workbench/vault-init-card.tsx",
  ];

  for (const path of removedPaths) {
    assert.equal(existsSync(join(process.cwd(), path)), false, `${path} should be removed`);
  }
});

test("wiki is a knowledge board with a secondary graph view", () => {
  const wikiSource = readFileSync(join(process.cwd(), "app/app/wiki/page.tsx"), "utf8");
  const boardSource = readFileSync(join(process.cwd(), "components/workbench/knowledge-board.tsx"), "utf8");
  const detailSource = readFileSync(join(process.cwd(), "app/app/wiki/[id]/page.tsx"), "utf8");

  assert.match(wikiSource, /KnowledgeBoard/);
  assert.match(wikiSource, /InkdeskGraphBoard/);
  assert.match(boardSource, /生成主题简报/);
  assert.match(boardSource, /项目知识主题/);
  assert.match(detailSource, /当前理解/);
  assert.match(detailSource, /关键决策/);
  assert.match(detailSource, /来源与相关资料/);
});
