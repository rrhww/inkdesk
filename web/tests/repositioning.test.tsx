import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import AppPage from "../app/app/page";
import { AppSidebarContent } from "../components/app-sidebar";
import { EditorView } from "../components/editor-view";
import * as mockData from "../lib/mock-data";

function compact(html: string) {
  return html.replace(/\s+/g, " ");
}

(globalThis as typeof globalThis & { React: typeof React }).React = React;

test("mock data exposes author, project, agent, and planning content for the repositioned product", () => {
  assert.ok("authorProfile" in mockData, "expected author profile data");
  assert.ok("publicProjects" in mockData, "expected curated public project data");
  assert.ok("publicKnowledgeBuckets" in mockData, "expected curated public knowledge buckets");
  assert.ok("publicUpdates" in mockData, "expected mixed public update stream");
  assert.ok("agentSuggestions" in mockData, "expected agent suggestion data");
  assert.ok("plans" in mockData, "expected task and planning data");
  assert.ok("workbenchSummary" in mockData, "expected workbench summary data");
  assert.equal(mockData.workbenchSummary.activePlans, 2);
  assert.equal(mockData.workbenchSummary.privateNotes, 1);
  assert.equal(mockData.workbenchSummary.publishedNotes, 2);
  assert.equal(mockData.publicKnowledgeBuckets.length, 4);
  assert.equal(mockData.publicProjects.length >= 2, true);
  assert.equal(mockData.publicUpdates.some((item) => item.type === "project"), true);
});

test("mock data source exposes split domain access for public, workbench, tags, and settings", async () => {
  const module = await import("../lib/mock-data-source");
  const source = module.mockInkdeskDataSource;
  const publicHome = source.getPublicHomeData();
  const workbench = source.getWorkbenchSnapshot();
  const tags = source.getTagRecords();
  const settings = source.getSettingsRecord();

  assert.ok("knowledgeBuckets" in publicHome, "expected public home data to include knowledge buckets");
  assert.equal(publicHome.knowledgeBuckets.length, 4);
  assert.ok("featuredProjects" in publicHome, "expected public home data to include featured projects");
  assert.equal(publicHome.featuredProjects.length > 0, true);
  assert.ok("recentUpdates" in publicHome, "expected public home data to include recent updates");
  assert.equal(publicHome.recentUpdates.some((item) => item.type === "article"), true);
  assert.ok("focusPlan" in workbench, "expected workbench snapshot to include a focus plan");
  assert.ok("quickActions" in workbench, "expected workbench snapshot to include quick actions");
  assert.ok(tags.length > 0, "expected tag records");
  assert.ok(settings.profile.displayName.length > 0, "expected settings profile");
});

test("public data helper returns undefined for a missing article slug", async () => {
  const module = await import("../lib/public");
  const article = await module.getPublicArticleBySlug("missing-slug");

  assert.equal(article, undefined);
});

test("public data helper returns undefined for a missing topic slug", async () => {
  const module = await import("../lib/public");
  const topic = await module.getPublicKnowledgeBucketBySlug("missing-topic");

  assert.equal(topic, undefined);
});

test("public data helper returns undefined for a missing project slug", async () => {
  const module = await import("../lib/public");
  const project = await module.getPublicProjectBySlug("missing-project");

  assert.equal(project, undefined);
});

test("knowledge workflow mock data exposes visibility metadata and retrieval helpers", () => {
  assert.ok("knowledgeHubSummary" in mockData, "expected knowledge hub summary");
  assert.ok("filterKnowledgeNotes" in mockData, "expected note filtering helper");
  assert.ok("searchKnowledgeNotes" in mockData, "expected note search helper");
  assert.equal(mockData.knowledgeHubSummary.totalNotes, 3);
  assert.equal(mockData.knowledgeHubSummary.privateNotes, 1);
  assert.equal(mockData.knowledgeHubSummary.publicNotes, 2);
  assert.equal(mockData.knowledgeHubSummary.linkedNotes, 3);
  assert.equal(mockData.notes[0].visibilityLabel, "已发布");
  assert.equal(mockData.notes[1].knowledgeStateLabel, "仅主系统");

  const searchHits = mockData.searchKnowledgeNotes("agent");

  assert.equal(searchHits[0]?.note.id, "note-002");
  assert.match(searchHits[0]?.hitLabels.join(" ") ?? "", /标题|标签/);
});

test("plan workflow mock data exposes execution summaries and knowledge linkage", () => {
  assert.ok("planWorkbenchSummary" in mockData, "expected plan workbench summary");
  assert.ok("getPlanWorkflowLanes" in mockData, "expected plan workflow lanes helper");
  assert.ok("getNotesByIds" in mockData, "expected plan-to-note helper");
  assert.equal(mockData.planWorkbenchSummary.todayPlans, 1);
  assert.equal(mockData.planWorkbenchSummary.activePlans, 2);
  assert.equal(mockData.planWorkbenchSummary.queuedPlans, 1);
  assert.equal(mockData.planWorkbenchSummary.linkedNotes, 3);
  assert.ok(mockData.plans[0].relatedNoteIds.length > 0, "expected plans to reference knowledge assets");

  const lanes = mockData.getPlanWorkflowLanes();

  assert.equal(lanes[0]?.title, "今天推进");
  assert.equal(lanes[1]?.title, "持续推进");
  assert.equal(lanes[2]?.title, "等待下一轮");
  assert.equal(mockData.getNotesByIds(mockData.plans[1]?.relatedNoteIds ?? [])[0]?.id, "note-001");
});

test("agent console page makes the agent the first thing the owner sees", async () => {
  const element = await AppPage();
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /工作台摘要/);
  assert.match(html, /Agent 控制台/);
  assert.match(html, /快速动作/);
  assert.match(html, /进行中计划/);
  assert.match(html, /待整理知识/);
  assert.match(html, /待发布内容/);
  assert.match(html, /返回当前焦点/);
});

test("sidebar prioritizes Agent, notes, plans, search, and publish in that order across shell navigation", () => {
  const html = compact(renderToStaticMarkup(AppSidebarContent({ pathname: "/app/plans" })));
  const markers = [
    'href="/app"><span class="material-symbols-outlined text-base">smart_toy</span><span class="font-headline font-medium">Agent',
    'href="/app/library"><span class="material-symbols-outlined text-base">book_5</span><span class="font-headline font-medium">笔记',
    'href="/app/plans"><span class="material-symbols-outlined text-base">checklist</span><span class="font-headline font-medium">任务与计划',
    'href="/app/search"><span class="material-symbols-outlined text-base">search</span><span class="font-headline font-medium">检索',
    'href="/app/publish"><span class="material-symbols-outlined text-base">publish</span><span class="font-headline font-medium">发布'
  ];
  const positions = markers.map((marker) => html.indexOf(marker));

  positions.forEach((position, index) => {
    assert.notEqual(position, -1, `expected sidebar marker ${markers[index]}`);
  });

  for (let index = 1; index < positions.length; index += 1) {
    assert.ok(positions[index] > positions[index - 1], "expected navigation order to match product priority");
  }

  assert.match(html, /主系统导航/);
  assert.match(html, /标签/);
  assert.match(html, /设置/);
  assert.match(html, /aria-current="page"/);
});

test("public home view presents the author portal without exposing a system login CTA", async () => {
  const module = await import("../components/public-home-view");
  const html = compact(renderToStaticMarkup(await module.PublicHomeView()));

  assert.match(html, /开发技术/);
  assert.match(html, /计算机基础/);
  assert.match(html, /项目实践/);
  assert.match(html, /方法与思考/);
  assert.match(html, /精选项目/);
  assert.match(html, /最近更新/);
  assert.match(html, /保持联系/);
  assert.match(html, /\/topics\/development-tech/);
  assert.match(html, /\/projects\/inkdesk-main-system/);
  assert.doesNotMatch(html, /研究主题/);
  assert.doesNotMatch(html, /公开统计/);
  assert.doesNotMatch(html, /登录/);
  assert.doesNotMatch(html, /进入工作区/);
});

test("public topic page presents curated category context, related writing, and cross-category navigation", async () => {
  const module = await import("../app/topics/[slug]/page");
  const element = await module.default({
    params: Promise.resolve({
      slug: "development-tech"
    })
  });
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /开发技术/);
  assert.match(html, /Java/);
  assert.match(html, /前端/);
  assert.match(html, /数据库/);
  assert.match(html, /代表文章/);
  assert.match(html, /相关文章/);
  assert.match(html, /相关项目/);
  assert.match(html, /其他分类/);
  assert.match(html, /给中后台页面做一次真正可维护的前端分层/);
  assert.match(html, /Inkdesk 主系统/);
  assert.match(html, /\/topics\/computer-fundamentals/);
  assert.match(html, /\/projects\/inkdesk-main-system/);
});

test("public project page presents project status, highlights, related writing, and category links", async () => {
  const module = await import("../app/projects/[slug]/page");
  const element = await module.default({
    params: Promise.resolve({
      slug: "inkdesk-main-system"
    })
  });
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /项目/);
  assert.match(html, /Inkdesk 主系统/);
  assert.match(html, /当前阶段/);
  assert.match(html, /亮点与方法/);
  assert.match(html, /相关笔记/);
  assert.match(html, /相关分类/);
  assert.match(html, /\/topics\/project-practice/);
  assert.match(html, /\/articles\/super-personal-workbench-reframe/);
});

test("plans page works as an execution console tied to knowledge and agent context", async () => {
  const module = await import("../app/app/plans/page");
  const element = await module.default();
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /执行摘要/);
  assert.match(html, /今天推进/);
  assert.match(html, /持续推进/);
  assert.match(html, /等待下一轮/);
  assert.match(html, /关联知识/);
  assert.match(html, /下一步动作/);
  assert.match(html, /Agent 协同/);
  assert.match(html, /为什么主系统首页必须先看到 Agent/);
  assert.match(html, /继续检索/);
});

test("library page acts as a knowledge hub with summary and filters", async () => {
  const module = await import("../app/app/library/page");
  const element = await module.default({
    searchParams: Promise.resolve({
      filter: "private"
    })
  });
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /知识摘要/);
  assert.match(html, /全部/);
  assert.match(html, /仅主系统/);
  assert.match(html, /已发布/);
  assert.match(html, /最近更新/);
  assert.match(html, /被计划与 Agent 调用/);
  assert.match(html, /当前筛选/);
  assert.match(html, /标签高频主题/);
  assert.match(html, /最近活动/);
});

test("search page shows retrieval prompts when idle", async () => {
  const module = await import("../app/app/search/page");
  const element = await module.default({
    searchParams: Promise.resolve({})
  });
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /近期知识/);
  assert.match(html, /示例搜索/);
  assert.match(html, /推荐召回/);
  assert.match(html, /最近搜索/);
});

test("search page ranks lowercase queries and shows hit labels", async () => {
  const module = await import("../app/app/search/page");
  const element = await module.default({
    searchParams: Promise.resolve({
      q: "agent"
    })
  });
  const html = compact(renderToStaticMarkup(element));
  const first = html.indexOf("为什么主系统首页必须先看到 Agent");
  const second = html.indexOf("把 Inkdesk 从知识库改造成超级个人工作台");

  assert.match(html, /命中来源/);
  assert.ok(first !== -1 && second !== -1 && first < second, "expected title and tag hit to rank first");
});

test("search page reports when no related context is found", async () => {
  const module = await import("../app/app/search/page");
  const element = await module.default({
    searchParams: Promise.resolve({
      q: "no-such-context"
    })
  });
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /当前没有召回到相关上下文/);
  assert.match(html, /推荐召回/);
});

test("editor view exposes knowledge asset metadata and workflow actions", () => {
  const html = compact(renderToStaticMarkup(<EditorView noteId="note-002" status="draft" />));

  assert.match(html, /编辑/);
  assert.match(html, /预览/);
  assert.match(html, /只读/);
  assert.match(html, /可见范围/);
  assert.match(html, /自动保存/);
  assert.match(html, /最近更新时间/);
  assert.match(html, /关联计划/);
  assert.match(html, /返回知识库/);
  assert.match(html, /以当前内容继续检索/);
  assert.match(html, /查看关联计划/);
  assert.match(html, /打开发布模块/);
});

test("publish page behaves like a publishing console for knowledge assets", async () => {
  const module = await import("../app/app/publish/page");
  const element = await module.default();
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /发布摘要/);
  assert.match(html, /知识输出路径/);
  assert.match(html, /继续整理后发布/);
  assert.match(html, /预览公共文章/);
  assert.match(html, /撤回到主系统/);
  assert.match(html, /来源知识资产/);
  assert.match(html, /回到知识资产/);
});

test("tags page organizes knowledge, plans, and public output around tags", async () => {
  const module = await import("../app/app/tags/page");
  const element = await module.default();
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /标签总览/);
  assert.match(html, /使用次数/);
  assert.match(html, /关联计划/);
  assert.match(html, /进入知识库/);
  assert.match(html, /公开内容/);
});

test("settings page exposes profile, workbench, editor, publish, and security groups", async () => {
  const module = await import("../app/app/settings/page");
  const element = await module.default();
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /作者公开资料/);
  assert.match(html, /主系统显示偏好/);
  assert.match(html, /编辑器默认项/);
  assert.match(html, /发布默认项/);
  assert.match(html, /会话与安全/);
});

test("public article page keeps public-only provenance and related reading", async () => {
  const module = await import("../app/articles/[slug]/page");
  const element = await module.default({
    params: Promise.resolve({
      slug: "super-personal-workbench-reframe"
    })
  });
  const html = compact(renderToStaticMarkup(element));

  assert.match(html, /公开文章/);
  assert.match(html, /这篇文章来自 Inkdesk 主系统中的长期知识资产/);
  assert.match(html, /相关分类/);
  assert.match(html, /相关项目/);
  assert.match(html, /\/topics\/project-practice/);
  assert.match(html, /\/projects\/inkdesk-main-system/);
  assert.match(html, /继续阅读/);
  assert.match(html, /返回公开输出/);
  assert.doesNotMatch(html, /继续探索此研究方向/);
  assert.doesNotMatch(html, /\/research\//);
  assert.doesNotMatch(html, /登录/);
  assert.doesNotMatch(html, /\/login/);
});

test("login page exposes a more robust owner-only form", async () => {
  const module = await import("../components/workbench/owner-login-form");
  const html = compact(
    renderToStaticMarkup(
      module.OwnerLoginForm({
        action: async () => {},
        hasError: false
      })
    )
  );

  assert.match(html, /主人身份/);
  assert.match(html, /type="email"/);
  assert.match(html, /autoComplete="username"/);
  assert.match(html, /autoComplete="current-password"/);
  assert.match(html, /required=""/);
});

test("not found pages provide clear public and private recovery paths", async () => {
  const rootNotFound = await import("../app/not-found");
  const appNotFound = await import("../app/app/not-found");
  const rootHtml = compact(renderToStaticMarkup(rootNotFound.default()));
  const appHtml = compact(renderToStaticMarkup(appNotFound.default()));

  assert.match(rootHtml, /返回公开输出首页/);
  assert.match(rootHtml, /这个页面没有被公开出来/);
  assert.match(appHtml, /回到 Agent 控制台/);
  assert.match(appHtml, /这条主系统路径当前不存在/);
});
