import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";
import { join } from "node:path";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { researchDashboardFixture } from "../lib/mock/research-fixtures";

function compact(html: string) {
  return html.replace(/\s+/g, " ");
}

async function captureConsoleDuring(run: () => Promise<void> | void) {
  const originalError = console.error;
  const originalWarn = console.warn;
  const messages: string[] = [];

  console.error = (...args: unknown[]) => {
    messages.push(args.map(String).join(" "));
  };
  console.warn = (...args: unknown[]) => {
    messages.push(args.map(String).join(" "));
  };

  try {
    await run();
  } finally {
    console.error = originalError;
    console.warn = originalWarn;
  }

  return messages;
}

(globalThis as typeof globalThis & { React: typeof React }).React = React;

test("ask-first workspace becomes the authenticated home experience", async () => {
  const module = await import("../app/app/page");
  const html = compact(
    renderToStaticMarkup(
      await module.default({
        searchParams: Promise.resolve({})
      })
    )
  );

  assert.match(html, /研究问答/);
  assert.match(html, /先看当前缺什么证据，再决定下一步/);
  assert.match(html, /判断面板/);
  assert.match(html, /建议提问/);
  assert.match(html, /下一步动作/);
  assert.match(html, /知识缺口/);
  assert.match(html, /name="q"/);
  assert.doesNotMatch(html, /任务与计划/);
  assert.doesNotMatch(html, /待发布内容/);
});

test("legacy compatibility app routes are no longer product entry points", () => {
  const legacyRouteFiles = [
    "app/app/inbox/page.tsx",
    "app/app/sources/page.tsx",
    "app/app/review/page.tsx",
    "app/app/topics/page.tsx",
    "app/app/topics/[id]/page.tsx"
  ];

  for (const routeFile of legacyRouteFiles) {
    assert.equal(existsSync(join(process.cwd(), routeFile)), false, `${routeFile} should be removed`);
  }
});

test("sidebar becomes a history-first research rail", async () => {
  const { AppSidebarContent } = await import("../components/app-sidebar");
  const html = compact(renderToStaticMarkup(AppSidebarContent({ pathname: "/app/ingest", snapshot: researchDashboardFixture })));
  const markers = [
    'href="/app"',
    'href="/app/ingest"',
    'href="/app/raw"'
  ];
  const positions = markers.map((marker) => html.indexOf(marker));

  positions.forEach((position, index) => {
    assert.notEqual(position, -1, `expected sidebar marker ${markers[index]}`);
  });

  for (let index = 1; index < positions.length; index += 1) {
    assert.ok(positions[index] > positions[index - 1], "expected navigation order to match research priority");
  }

  assert.match(html, /LLM Wiki/);
  assert.match(html, /最近对话/);
  assert.match(html, /新建对话/);
  assert.match(html, /当前主题/);
  assert.match(html, /待审阅/);
  assert.match(html, /最新资料/);
  assert.doesNotMatch(html, /任务与计划/);
  assert.doesNotMatch(html, /发布/);
  assert.doesNotMatch(html, /标签/);
  assert.doesNotMatch(html, /设置/);
  assert.match(html, /aria-current="page"/);
});

test("raw page presents imported files waiting for ingest", async () => {
  const module = await import("../app/app/raw/page");
  const warnings = await captureConsoleDuring(async () => {
    renderToStaticMarkup(await module.default());
  });
  const html = compact(renderToStaticMarkup(await module.default()));

  assert.match(html, /raw/);
  assert.match(html, /原始材料/);
  assert.match(html, /vault/);
  assert.match(html, /迁移旧笔记/);
  assert.match(html, /WEB/);
  assert.match(html, /PDF/);
  assert.match(html, /raw\//);
  assert.match(html, /name="url"/);
  assert.match(html, /name="body"/);
  assert.match(html, /type="file"/);
  assert.equal(warnings.length, 0);
});

test("wiki index and detail pages expose compiled understanding, open questions, and provenance", async () => {
  const wikiPage = await import("../app/app/wiki/page");
  const wikiDetailPage = await import("../app/app/wiki/[id]/page");
  const wikiHtml = compact(renderToStaticMarkup(await wikiPage.default()));
  const detailHtml = compact(
    renderToStaticMarkup(
      await wikiDetailPage.default({
        params: Promise.resolve({
          id: "topic-001"
        })
      })
    )
  );

  assert.match(wikiHtml, /wiki/);
  assert.match(wikiHtml, /Inkdesk repositioning/);
  assert.match(wikiHtml, /claim 治理总览/);
  assert.match(wikiHtml, /2 条高风险 claim 仍需处理/);
  assert.match(wikiHtml, /1 条缺少直接证据/);
  assert.match(wikiHtml, /1 条需要重审/);
  assert.match(wikiHtml, /2 条 claim 存在冲突/);
  assert.match(wikiHtml, /知识页里仍有 claim 需要补证或重审/);
  assert.match(detailHtml, /Current Understanding/);
  assert.match(detailHtml, /Open Questions/);
  assert.match(detailHtml, /Key Claims/);
  assert.match(detailHtml, /Sources/);
  assert.match(detailHtml, /Research-first wiki note/);
  assert.match(detailHtml, /supported/i);
  assert.match(detailHtml, /最近验证/);
  assert.match(detailHtml, /最近使用/);
  assert.match(detailHtml, /使用 3 次/);
  assert.match(detailHtml, /证据 1 条/);
  assert.match(detailHtml, /最近已验证/);
  assert.match(detailHtml, /当前验证较新/);
  assert.match(detailHtml, /缺少直接证据/);
  assert.match(detailHtml, /存在冲突/);
  assert.match(detailHtml, /这条 claim 当前和同主题里的另一条判断互相打架/);
  assert.match(detailHtml, /wiki\//);
});

test("ingest, ask, and raw pages form the new core workflow", async () => {
  const ingestPage = await import("../app/app/ingest/page");
  const askPage = await import("../app/app/ask/page");
  const rawPage = await import("../app/app/raw/page");
  const appPage = await import("../app/app/page");

  const ingestHtml = compact(renderToStaticMarkup(await ingestPage.default({})));
  const askHtml = compact(
    renderToStaticMarkup(
      await askPage.default({
        searchParams: Promise.resolve({
          q: "这个主题当前最稳定的理解是什么？",
          topicId: "topic-001"
        })
      })
    )
  );
  const appHtml = compact(
    renderToStaticMarkup(
      await appPage.default({
        searchParams: Promise.resolve({
          q: "这个主题当前最稳定的理解是什么？",
          topicId: "topic-001"
        })
      })
    )
  );
  const rawHtml = compact(renderToStaticMarkup(await rawPage.default()));

  assert.match(ingestHtml, /ingest/);
  assert.match(ingestHtml, /TOPIC_PATCH/);
  assert.match(ingestHtml, /重审/);
  assert.match(ingestHtml, /提案解释/);
  assert.match(ingestHtml, /Topic 归属/);
  assert.match(ingestHtml, /证据来源/);
  assert.match(ingestHtml, /unsupported/i);
  assert.match(ingestHtml, /证据 0 条/);
  assert.match(ingestHtml, /接受写入 wiki/);
  assert.match(ingestHtml, /忽略提案/);
  assert.match(askHtml, /研究问答/);
  assert.match(askHtml, /当前最稳定的理解/);
  assert.match(askHtml, /name="mode"/);
  assert.match(askHtml, /显式联网补料/);
  assert.match(askHtml, /沉淀到 wiki/);
  assert.match(askHtml, /置信度/);
  assert.match(askHtml, /知识缺口/);
  assert.match(askHtml, /继续追问/);
  assert.match(askHtml, /引用来源/);
  assert.match(askHtml, /<form/);
  assert.match(askHtml, /name="q"/);
  assert.match(askHtml, /name="topicId"/);
  assert.match(appHtml, /研究问答/);
  assert.match(appHtml, /判断面板/);
  assert.match(appHtml, /当前最稳定的理解/);
  assert.match(appHtml, /缺少直接证据/);
  assert.match(appHtml, /需要重审/);
  assert.match(appHtml, /claim 彼此冲突/);
  assert.match(rawHtml, /原始材料/);
  assert.match(rawHtml, /raw\//);
  assert.match(rawHtml, /legacy:\/\/note-001/);
});

test("ask page surfaces follow-up context and external web evidence boundaries", async () => {
  const askPage = await import("../app/app/ask/page");
  const askHtml = compact(
    renderToStaticMarkup(
      await askPage.default({
        searchParams: Promise.resolve({
          q: "这个主题当前最稳定的理解是什么？",
          topicId: "topic-001",
          mode: "vault_plus_web",
          continueFromAskTurnId: "ask-prev"
        })
      })
    )
  );

  assert.match(askHtml, /正在延续上一轮问答/);
  assert.match(askHtml, /这些外部资料还没有进入你的 vault/);
  assert.match(askHtml, /沉淀到 wiki（会先保存外部来源到 raw）/);
  assert.match(askHtml, /continueFromAskTurnId=/);
});

test("ingest revalidation covers ask alias and affected wiki routes", async () => {
  const module = await import("../app/app/ingest/revalidation-paths");

  assert.deepEqual(module.buildIngestRevalidationPaths(), ["/app", "/app/ask", "/app/ingest", "/app/wiki", "/app/raw"]);
  assert.deepEqual(module.buildIngestRevalidationPaths("topic-001"), ["/app", "/app/ask", "/app/ingest", "/app/wiki", "/app/raw", "/app/wiki/topic-001"]);
});

test("login page now frames Inkdesk as a private research-first workspace", async () => {
  const module = await import("../app/login/page");
  const html = compact(renderToStaticMarkup(await module.default({ searchParams: Promise.resolve({}) })));

  assert.match(html, /进入私有 LLM Wiki/);
  assert.match(html, /Ask-first 工作区/);
  assert.match(html, /继续追问、补 raw、审 ingest 或打开 wiki/);
  assert.doesNotMatch(html, /Today Vault Panel/);
  assert.doesNotMatch(html, /任务计划与公开内容输出/);
});
