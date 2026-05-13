import assert from "node:assert/strict";
import test from "node:test";
import type { ResearchAskBriefing, ResearchAskRequest, ResearchAskResponse } from "../lib/types";

type FetchCall = {
  input: RequestInfo | URL;
  init?: RequestInit;
};

function createJsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json"
    }
  });
}

async function withMockedFetch(
  responder: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> | Response,
  run: (calls: FetchCall[]) => Promise<void>
) {
  const originalFetch = globalThis.fetch;
  const calls: FetchCall[] = [];

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ input, init });
    return responder(input, init);
  }) as typeof fetch;

  try {
    await run(calls);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

test("research helper calls the backend dashboard and preserves the vault-first shape", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/admin/home") {
      assert.equal((init?.headers as Record<string, string> | undefined)?.Cookie, "inkvault_owner_session=owner");

      return createJsonResponse({
        summary: {
          activeTopics: 2,
          pendingReviews: 3,
          inboxSources: 4,
          totalSources: 7
        },
        health: {
          rawBacklogCount: 4,
          reviewBacklogCount: 3,
          openQuestionCount: 2,
          knowledgeGapCount: 1,
          writebackCandidateCount: 1,
          unsupportedClaimCount: 1,
          staleClaimCount: 1,
          conflictingClaimCount: 2,
          signals: [
            {
              type: "RAW_BACKLOG",
              severity: "warning",
              title: "raw 里有 4 条材料等待编译",
              summary: "这些来源还没有进入 wiki 记忆。",
              relatedId: "source-001",
              relatedTitle: "Research-first wiki note"
            },
            {
              type: "REVIEW_BACKLOG",
              severity: "warning",
              title: "ingest 队列有 3 条待审阅提案",
              summary: "需要接受或忽略后才会改变 wiki。",
              relatedId: "review-001",
              relatedTitle: "把来源补充进现有主题"
            },
            {
              type: "OPEN_QUESTIONS",
              severity: "info",
              title: "wiki 里还有 2 个开放问题",
              summary: "开放问题提示下一轮需要补证的方向。",
              relatedId: "topic-001",
              relatedTitle: "Inkvault repositioning"
            },
            {
              type: "UNSUPPORTED_CLAIM",
              severity: "warning",
              title: "有 1 条 claim 缺少直接证据",
              summary: "至少有一条关键结论还没有直接证据链支持。",
              relatedId: "topic-001",
              relatedTitle: "Inkvault repositioning"
            },
            {
              type: "STALE_CLAIM",
              severity: "warning",
              title: "有 1 条常用 claim 需要重审",
              summary: "这条 claim 最近仍被 Ask 使用，但验证时间过旧或证据仍偏弱。",
              relatedId: "topic-001",
              relatedTitle: "Inkvault repositioning"
            },
            {
              type: "CONFLICTING_CLAIM",
              severity: "warning",
              title: "有 2 条 claim 彼此冲突",
              summary: "同一主题里出现了方向相反的 claim，建议回到 ingest 统一裁决。",
              relatedId: "topic-001",
              relatedTitle: "Inkvault repositioning"
            }
          ]
        },
        focusTopic: {
          id: "topic-001",
          title: "Inkvault repositioning",
          summary: "把产品中心收回到 Topic。",
          sourceCount: 3,
          openQuestionCount: 2,
          unsupportedClaimCount: 1,
          staleClaimCount: 1,
          updatedAt: "2026-04-13T09:30:00Z"
        },
        recentSources: [
          {
            id: "source-001",
            kind: "WEB",
            status: "INGEST_PENDING",
            title: "Research-first wiki note",
            locator: "https://example.com/wiki",
            excerpt: "强调 Topic-first 的研究工作流。",
            legacyNoteId: null,
            vaultPath: "raw/2026-04-13-research-first-wiki-note.md",
            contentHash: "raw-hash",
            updatedAt: "2026-04-13T08:00:00Z"
          }
        ],
        pendingReviews: [
          {
            id: "review-001",
            kind: "TOPIC_PATCH",
            proposalKind: "TOPIC_PATCH",
            title: "把来源补充进现有主题",
            summary: "提议把新来源编译进 Inkvault repositioning。",
            sourceId: "source-001",
            sourceTitle: "Research-first wiki note",
            targetTopicId: "topic-001",
            targetTopicTitle: "Inkvault repositioning",
            proposedTopicTitle: null,
            proposedUnderstanding: "Topic 应成为产品主对象。",
            proposedOpenQuestions: "迁移老笔记时，哪些内容应进入 Topic？",
            proposedClaim: "Topic 应成为产品主对象。",
            proposedVaultPath: "wiki/inkvault-repositioning.md",
            sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
            proposalPayload: {
              topicDecision: {
                decision: "PATCH",
                targetTopicId: "topic-001",
                targetTopicTitle: "Inkvault repositioning",
                proposedTopicTitle: null
              },
              summaryChanges: ["Topic 应成为产品主对象。"],
              claims: [
                {
                  statement: "Topic 应成为产品主对象。",
                  citationLabel: "Research-first wiki note",
                  sourceId: "source-001",
                  supportingChunkIds: ["chunk-source-001"],
                  evidenceCount: 1,
                  provenanceStatus: "supported"
                }
              ],
              conflicts: [],
              openQuestions: ["迁移老笔记时，哪些内容应进入 Topic？"],
              explanation: "系统建议把这次 Ask / raw 结论补充进现有主题「Inkvault repositioning」，因为证据与当前主题最相关。",
              evidence: [
                {
                  sourceId: "source-001",
                  sourceTitle: "Research-first wiki note",
                  sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
                  locator: "https://example.com/wiki",
                  excerpt: "强调 Topic-first 的研究工作流。"
                }
              ]
            },
            createdAt: "2026-04-13T08:10:00Z"
          }
        ],
        suggestedQuestions: ["Topic 和 Source 的边界是什么？"]
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/research");
    const snapshot = await module.getResearchDashboard("owner");

    assert.equal(snapshot.summary.activeTopics, 2);
    assert.equal(snapshot.health.rawBacklogCount, 4);
    assert.equal(snapshot.health.signals[0]?.type, "RAW_BACKLOG");
    assert.equal(snapshot.health.unsupportedClaimCount, 1);
    assert.equal(snapshot.health.staleClaimCount, 1);
    assert.equal(snapshot.health.conflictingClaimCount, 2);
    assert.equal(snapshot.focusTopic?.id, "topic-001");
    assert.equal(snapshot.focusTopic?.unsupportedClaimCount, 1);
    assert.equal(snapshot.focusTopic?.staleClaimCount, 1);
    assert.equal(snapshot.pendingReviews[0]?.targetTopicTitle, "Inkvault repositioning");
    assert.equal(snapshot.pendingReviews[0]?.proposalPayload?.topicDecision.decision, "PATCH");
    assert.equal(snapshot.pendingReviews[0]?.proposalPayload?.claims[0]?.provenanceStatus, "supported");
    assert.equal(snapshot.pendingReviews[0]?.proposalPayload?.evidence[0]?.sourceVaultPath, "raw/2026-04-13-research-first-wiki-note.md");
    assert.equal(snapshot.recentSources[0]?.kind, "WEB");
    assert.equal(snapshot.recentSources[0]?.vaultPath, "raw/2026-04-13-research-first-wiki-note.md");
    assert.equal(snapshot.suggestedQuestions[0], "Topic 和 Source 的边界是什么？");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("research helper fetches wiki detail, raw list, ingest items, and grounded ask responses", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  const askRequest: ResearchAskRequest = {
    topicId: "topic-001",
    question: "这个主题当前最稳定的理解是什么？",
    mode: "vault_plus_web",
    continueFromAskTurnId: "ask-000"
  };

  const askResponse: ResearchAskResponse = {
    id: "ask-001",
    topicId: "topic-001",
    question: "这个主题当前最稳定的理解是什么？",
    answer: "当前最稳定的理解是 Topic 取代 Note 成为核心对象。",
    confidence: 0.72,
    followUpQuestions: ["这条理解还缺哪条外部证据？"],
    knowledgeGaps: ["当前 wiki 没有覆盖最新外部资料，需要显式联网补料。"],
    usedWikiIds: ["topic-001"],
    usedSourceIds: ["source-001"],
    usedWebSources: [
      {
        url: "https://example.com/web/topic-memory",
        title: "Topic memory web search",
        excerpt: "外部资料也支持 Topic-first 的研究工作流。",
        reasonUsed: "用于补足 wiki 里还没有覆盖的外部佐证。"
      }
    ],
    contextAskTurnIds: ["ask-000"],
    canWriteback: true,
    citations: [
      {
        sourceId: "source-001",
        title: "Research-first wiki note",
        kind: "WEB",
        locator: "https://example.com/wiki",
        vaultPath: "raw/2026-04-13-research-first-wiki-note.md"
      }
    ],
    createdAt: "2026-04-13T08:45:00Z"
  };

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/wiki/topic-001") {
      return createJsonResponse({
        id: "topic-001",
        title: "Inkvault repositioning",
        summary: "把产品中心收回到 Topic。",
        vaultPath: "wiki/inkvault-repositioning.md",
        contentHash: "wiki-hash",
        currentUnderstanding: ["Topic 是新的核心对象。"],
        openQuestions: ["哪些旧笔记应先迁移？"],
        sources: [
          {
            sourceId: "source-001",
            title: "Research-first wiki note",
            kind: "WEB",
            locator: "https://example.com/wiki",
            vaultPath: "raw/2026-04-13-research-first-wiki-note.md",
            legacyNoteId: null
          }
        ],
        keyClaims: [
          {
            id: "claim-001",
            statement: "Topic 是新的核心对象。",
            sourceId: "source-001",
            citationLabel: "Research-first wiki note",
            evidenceCount: 1,
            provenanceStatus: "supported",
            lastVerifiedAt: "2026-05-10T08:30:00Z",
            usageCount: 3,
            lastUsedAt: "2026-05-03T03:00:00Z",
            needsReview: false,
            hasConflict: true
          }
        ],
        thread: [
          {
            id: "thread-001",
            role: "ASSISTANT",
            content: "已把新来源编译进当前主题。",
            sourceId: "source-001",
            createdAt: "2026-04-13T08:30:00Z"
          }
        ],
        updatedAt: "2026-04-13T08:30:00Z"
      });
    }

    if (url.pathname === "/api/raw") {
      return createJsonResponse([
        {
          id: "source-001",
          kind: "WEB",
          status: "INGEST_PENDING",
          title: "Research-first wiki note",
          locator: "https://example.com/wiki",
          excerpt: "强调 Topic-first 的研究工作流。",
          legacyNoteId: null,
          vaultPath: "raw/2026-04-13-research-first-wiki-note.md",
          contentHash: "raw-hash",
          updatedAt: "2026-04-13T08:00:00Z"
        }
      ]);
    }

    if (url.pathname === "/api/ingest") {
      return createJsonResponse([
        {
          id: "review-001",
          kind: "TOPIC_PATCH",
          proposalKind: "TOPIC_PATCH",
          title: "把来源补充进现有主题",
          summary: "提议把新来源编译进 Inkvault repositioning。",
          sourceId: "source-001",
          sourceTitle: "Research-first wiki note",
          sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
          targetTopicId: "topic-001",
          targetTopicTitle: "Inkvault repositioning",
          proposedTopicTitle: null,
          proposedUnderstanding: "Topic 应成为产品主对象。",
          proposedOpenQuestions: "迁移老笔记时，哪些内容应进入 Topic？",
          proposedClaim: "Topic 应成为产品主对象。",
          proposedVaultPath: "wiki/inkvault-repositioning.md",
          proposalPayload: {
            topicDecision: {
              decision: "PATCH",
              targetTopicId: "topic-001",
              targetTopicTitle: "Inkvault repositioning",
              proposedTopicTitle: null
            },
            summaryChanges: ["Topic 应成为产品主对象。"],
            claims: [
              {
                statement: "Topic 应成为产品主对象。",
                citationLabel: "Research-first wiki note",
                sourceId: "source-001",
                supportingChunkIds: ["chunk-source-001"],
                evidenceCount: 1,
                provenanceStatus: "supported"
              }
            ],
            conflicts: [],
            openQuestions: ["迁移老笔记时，哪些内容应进入 Topic？"],
            explanation: "系统建议把这次 Ask / raw 结论补充进现有主题「Inkvault repositioning」，因为证据与当前主题最相关。",
            evidence: [
              {
                sourceId: "source-001",
                sourceTitle: "Research-first wiki note",
                sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
                locator: "https://example.com/wiki",
                excerpt: "强调 Topic-first 的研究工作流。"
              }
            ]
          },
          createdAt: "2026-04-13T08:10:00Z"
        }
      ]);
    }

    if (url.pathname === "/api/ask") {
      assert.equal(init?.method, "POST");
      assert.deepEqual(JSON.parse(String(init?.body)), askRequest);

      return createJsonResponse(askResponse);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/research");
    const [topic, sources, ingestItems, answer] = await Promise.all([
      module.getWikiDetail("topic-001", "owner"),
      module.getRawSources("owner"),
      module.getIngestItems("owner"),
      module.askResearch(
        askRequest,
        "owner"
      )
    ]);

    assert.equal(topic.keyClaims[0]?.citationLabel, "Research-first wiki note");
    assert.equal(topic.keyClaims[0]?.provenanceStatus, "supported");
    assert.equal(topic.keyClaims[0]?.usageCount, 3);
    assert.equal(topic.keyClaims[0]?.lastUsedAt, "2026-05-03T03:00:00Z");
    assert.equal(topic.keyClaims[0]?.needsReview, false);
    assert.equal(topic.keyClaims[0]?.hasConflict, true);
    assert.equal(topic.thread[0]?.role, "ASSISTANT");
    assert.equal(topic.vaultPath, "wiki/inkvault-repositioning.md");
    assert.equal(sources[0]?.status, "INGEST_PENDING");
    assert.equal(sources[0]?.vaultPath, "raw/2026-04-13-research-first-wiki-note.md");
    assert.equal(ingestItems[0]?.proposedVaultPath, "wiki/inkvault-repositioning.md");
    assert.equal(ingestItems[0]?.proposalPayload?.claims[0]?.statement, "Topic 应成为产品主对象。");
    assert.equal(answer.citations[0]?.sourceId, "source-001");
    assert.equal(answer.citations[0]?.vaultPath, "raw/2026-04-13-research-first-wiki-note.md");
    assert.equal(answer.confidence, 0.72);
    assert.equal(answer.followUpQuestions[0], "这条理解还缺哪条外部证据？");
    assert.equal(answer.knowledgeGaps[0], "当前 wiki 没有覆盖最新外部资料，需要显式联网补料。");
    assert.equal(answer.usedWikiIds[0], "topic-001");
    assert.equal(answer.usedSourceIds[0], "source-001");
    assert.equal(answer.contextAskTurnIds[0], "ask-000");
    assert.equal(answer.canWriteback, true);
    const firstWebSource = answer.usedWebSources[0];
    assert.ok(firstWebSource);
    assert.equal(firstWebSource.url, "https://example.com/web/topic-memory");
    assert.equal(firstWebSource.excerpt.toUpperCase(), "外部资料也支持 TOPIC-FIRST 的研究工作流。");
    assert.equal(firstWebSource.reasonUsed, "用于补足 wiki 里还没有覆盖的外部佐证。");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("research helper fetches ask briefing by scope", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  const workspaceBriefing: ResearchAskBriefing = {
    scope: "workspace",
    summary: "当前最需要先处理的是 ingest 队列。",
    confidence: 0.74,
    knowledgeGaps: [
      {
        title: "待审阅提案积压",
        detail: "还有 3 条 ingest 提案没有进入最终知识层。",
        href: "/app/ingest"
      },
      {
        title: "有 2 条 claim 彼此冲突",
        detail: "同一主题里出现了方向相反的 claim，建议先回到 ingest 做一轮统一裁决。",
        href: "/app/ingest"
      }
    ],
    nextActions: [
      {
        kind: "OPEN_INGEST",
        label: "打开审阅队列",
        description: "先处理最靠前的提案，再继续提问。",
        href: "/app/ingest"
      },
      {
        kind: "OPEN_INGEST",
        label: "处理 claim 冲突",
        description: "回到 ingest 统一裁决互相打架的 claim，避免继续带着冲突理解推进。",
        href: "/app/ingest"
      }
    ],
    suggestedQuestions: ["当前哪条提案最值得先审阅？"],
    supportingSignals: [
      {
        type: "REVIEW_BACKLOG",
        title: "ingest 队列有 3 条待审阅提案",
        summary: "这些提案需要人工确认。",
        href: "/app/ingest"
      },
      {
        type: "CONFLICTING_CLAIM",
        title: "有 2 条 claim 彼此冲突",
        summary: "同一主题里出现了方向相反的 claim，建议回到 ingest 统一裁决。",
        href: "/app/ingest"
      }
    ],
    generatedAt: "2026-05-11T09:00:00Z"
  };

  await withMockedFetch(async (input) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/ask/briefing" && url.search === "") {
      return createJsonResponse(workspaceBriefing);
    }

    if (url.pathname === "/api/ask/briefing" && url.search === "?topicId=topic-001") {
      return createJsonResponse({
        ...workspaceBriefing,
        scope: "topic",
        topicId: "topic-001",
        topicTitle: "Inkvault repositioning"
      });
    }

    if (url.pathname === "/api/ask/briefing" && url.search === "?askTurnId=ask-001") {
      return createJsonResponse({
        ...workspaceBriefing,
        scope: "ask_turn",
        askTurnId: "ask-001"
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/research");
    const [workspace, topic, askTurn] = await Promise.all([
      module.getAskBriefing(undefined, "owner"),
      module.getAskBriefing({ topicId: "topic-001" }, "owner"),
      module.getAskBriefing({ askTurnId: "ask-001" }, "owner")
    ]);

    assert.equal(workspace.scope, "workspace");
    assert.equal(topic.topicId, "topic-001");
    assert.equal(topic.topicTitle, "Inkvault repositioning");
    assert.equal(askTurn.askTurnId, "ask-001");
    assert.equal(askTurn.nextActions[0]?.kind, "OPEN_INGEST");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("research helper returns ingest review decisions so pages can refresh affected routes", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/ingest/review-001/accept") {
      assert.equal(init?.method, "POST");
      return createJsonResponse({
        reviewId: "review-001",
        status: "ACCEPTED",
        topicId: "topic-001"
      });
    }

    if (url.pathname === "/api/ingest/review-001/reject") {
      assert.equal(init?.method, "POST");
      return createJsonResponse({
        reviewId: "review-001",
        status: "REJECTED",
        topicId: null
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/research");
    const accepted = await module.acceptIngest("review-001", "owner");
    const rejected = await module.rejectIngest("review-001", "owner");

    assert.equal(accepted.reviewId, "review-001");
    assert.equal(accepted.status, "ACCEPTED");
    assert.equal(accepted.topicId, "topic-001");
    assert.equal(rejected.reviewId, "review-001");
    assert.equal(rejected.status, "REJECTED");
    assert.equal(rejected.topicId, null);
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("research helper falls back to local research fixtures when API base URL is missing", async () => {
  delete process.env.NEXT_PUBLIC_API_BASE_URL;

  await withMockedFetch(async () => {
    throw new Error("fetch should not run without an API base URL");
  }, async () => {
    const module = await import("../lib/research");
    const snapshot = await module.getResearchDashboard();

    assert.equal(snapshot.summary.activeTopics > 0, true);
    assert.equal(snapshot.health.signals.length >= 3, true);
    assert.equal(snapshot.pendingReviews.length > 0, true);
    assert.equal(snapshot.recentSources.length > 0, true);
  });
});

test("research helper imports raw sources through dedicated web text and pdf entrypoints", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/raw/web") {
      assert.equal(init?.method, "POST");
      assert.deepEqual(JSON.parse(String(init?.body)), {
        url: "https://example.com/topic-memory",
        title: "Topic memory capture"
      });
      return createJsonResponse({ id: "source-web-001" }, 201);
    }

    if (url.pathname === "/api/raw") {
      assert.equal(init?.method, "POST");
      assert.deepEqual(JSON.parse(String(init?.body)), {
        kind: "TEXT",
        title: "Manual note",
        locator: "local://note",
        excerpt: "Manual excerpt",
        body: "Manual body"
      });
      return createJsonResponse({ id: "source-text-001" }, 201);
    }

    if (url.pathname === "/api/raw/pdf") {
      assert.equal(init?.method, "POST");
      assert.ok(init?.body instanceof FormData);
      assert.equal(init.body.get("title"), "Topic memory PDF");
      const file = init.body.get("file");
      assert.ok(file instanceof File);
      assert.equal(file.name, "topic-memory.pdf");
      return createJsonResponse({ id: "source-pdf-001" }, 201);
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/research");
    await module.importWebSource(
      {
        url: "https://example.com/topic-memory",
        title: "Topic memory capture"
      },
      "owner"
    );
    await module.importTextSource(
      {
        title: "Manual note",
        locator: "local://note",
        excerpt: "Manual excerpt",
        body: "Manual body"
      },
      "owner"
    );
    await module.importPdfSource(new File(["pdf"], "topic-memory.pdf", { type: "application/pdf" }), "Topic memory PDF", "owner");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

test("research helper can turn an explicit ask answer card into an ingest proposal", async () => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8080";

  await withMockedFetch(async (input, init) => {
    const url = new URL(String(input));

    if (url.pathname === "/api/ask/ask-001/writeback") {
      assert.equal(init?.method, "POST");
      return createJsonResponse({
        id: "review-ask-001",
        kind: "TOPIC_PATCH",
        proposalKind: "TOPIC_PATCH",
        title: "把 Ask 结论补充进现有主题",
        summary: "把“这个主题当前最稳定的理解是什么？”的回答沉淀进 Inkvault repositioning。",
        sourceId: "source-001",
        sourceTitle: "Research-first wiki note",
        sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
        targetTopicId: "topic-001",
        targetTopicTitle: "Inkvault repositioning",
        proposedTopicTitle: null,
        proposedUnderstanding: "当前最稳定的理解是 Topic 取代 Note 成为核心对象。",
        proposedOpenQuestions: "这条理解还缺哪条外部证据？",
        proposedClaim: "当前最稳定的理解是 Topic 取代 Note 成为核心对象。",
        proposedVaultPath: "wiki/inkvault-repositioning.md",
        proposalPayload: {
          topicDecision: {
            decision: "PATCH",
            targetTopicId: "topic-001",
            targetTopicTitle: "Inkvault repositioning",
            proposedTopicTitle: null
          },
          summaryChanges: ["把 Ask 当前回答补充进 Inkvault repositioning 的 Current Understanding。"],
          claims: [
            {
              statement: "当前最稳定的理解是 Topic 取代 Note 成为核心对象。",
              citationLabel: "Research-first wiki note",
              sourceId: "source-001",
              supportingChunkIds: ["chunk-source-001"],
              evidenceCount: 1,
              provenanceStatus: "supported"
            }
          ],
          conflicts: [],
          openQuestions: ["这条理解还缺哪条外部证据？"],
          explanation: "系统建议把这次 Ask 结论补充进现有主题「Inkvault repositioning」，因为当前回答已经命中了该主题的现有知识页。",
          evidence: [
            {
              sourceId: "source-001",
              sourceTitle: "Research-first wiki note",
              sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
              locator: "https://example.com/wiki",
              excerpt: "强调 Topic-first 的研究工作流。"
            }
          ]
        },
        createdAt: "2026-04-13T08:50:00Z"
      });
    }

    throw new Error(`Unexpected fetch URL: ${url.toString()}`);
  }, async () => {
    const module = await import("../lib/research");
    const review = await module.proposeAskWriteback("ask-001", "owner");

    assert.equal(review.id, "review-ask-001");
    assert.equal(review.targetTopicId, "topic-001");
    assert.equal(review.proposalPayload?.topicDecision.decision, "PATCH");
  });

  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});
