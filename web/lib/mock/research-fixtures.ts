import type {
  ResearchAskBriefing,
  ResearchAskHistoryEntry,
  ResearchAskRequest,
  ResearchAskResponse,
  ResearchDashboard,
  ResearchReviewItem,
  ResearchSourceRecord,
  ResearchTopicDetail,
  ResearchTopicSummary
} from "@/lib/types";

export const researchSourcesFixture: ResearchSourceRecord[] = [
  {
    id: "source-004",
    kind: "WEB",
    status: "INGEST_PENDING",
    title: "Research-first wiki note",
    locator: "https://example.com/wiki",
    excerpt: "强调 wiki-first 的研究工作流。",
    legacyNoteId: null,
    vaultPath: "raw/2026-04-13-research-first-wiki-note.md",
    contentHash: "mock-raw-web",
    updatedAt: "2026-04-13T08:00:00Z"
  },
  {
    id: "source-005",
    kind: "PDF",
    status: "WIKI_LINKED",
    title: "Wiki memory compilation notes",
    locator: "file:///research/topic-memory.pdf",
    excerpt: "PDF 强调 AI 先编译、人再审阅的节奏。",
    legacyNoteId: null,
    vaultPath: "raw/2026-04-13-topic-memory-compilation-notes.md",
    contentHash: "mock-raw-pdf",
    updatedAt: "2026-04-13T07:40:00Z"
  },
  {
    id: "source-002",
    kind: "LEGACY_NOTE",
    status: "INGEST_PENDING",
    title: "为什么 Today Vault Panel 应成为登录后的第一屏",
    locator: "legacy://note-002",
    excerpt: "迁移材料强调首页先看到研究驾驶舱，而不是旧式文档列表。",
    legacyNoteId: "note-002",
    vaultPath: "raw/2026-04-12-today-vault-panel.md",
    contentHash: "mock-raw-legacy-2",
    updatedAt: "2026-04-12T07:42:00Z"
  },
  {
    id: "source-001",
    kind: "LEGACY_NOTE",
    status: "WIKI_LINKED",
    title: "将 Inkvault 重定位为私有研究型 LLM Wiki",
    locator: "legacy://note-001",
    excerpt: "迁移材料已经成为 wiki 迁移的核心 raw 来源。",
    legacyNoteId: "note-001",
    vaultPath: "raw/2026-04-12-inkvault-llm-wiki.md",
    contentHash: "mock-raw-legacy-1",
    updatedAt: "2026-04-12T08:10:00Z"
  },
  {
    id: "source-003",
    kind: "LEGACY_NOTE",
    status: "INGEST_PENDING",
    title: "ingest 队列如何保证 AI 编译可控",
    locator: "legacy://note-003",
    excerpt: "迁移材料指出 AI 编译必须经过 ingest 才能进入 wiki 记忆。",
    legacyNoteId: "note-003",
    vaultPath: "raw/2026-04-12-ingest-review-discipline.md",
    contentHash: "mock-raw-legacy-3",
    updatedAt: "2026-04-12T06:58:00Z"
  }
];

export const researchTopicSummariesFixture: ResearchTopicSummary[] = [
  {
    id: "topic-001",
    title: "Inkvault repositioning",
    summary: "把产品中心收回到 raw / ingest / wiki，由 raw 驱动、由 ingest 把关。",
    sourceCount: 3,
    openQuestionCount: 2,
    unsupportedClaimCount: 1,
    staleClaimCount: 1,
    conflictingClaimCount: 2,
    vaultPath: "wiki/inkvault-repositioning.md",
    updatedAt: "2026-04-13T08:30:00Z"
  },
  {
    id: "topic-002",
    title: "Today Vault Panel",
    summary: "首页应该先给出 raw、ingest 和 wiki 上下文，而不是旧的笔记或计划列表。",
    sourceCount: 1,
    openQuestionCount: 1,
    unsupportedClaimCount: 0,
    staleClaimCount: 0,
    conflictingClaimCount: 0,
    vaultPath: "wiki/today-vault-panel.md",
    updatedAt: "2026-04-12T11:20:00Z"
  }
];

export const researchReviewItemsFixture: ResearchReviewItem[] = [
  {
    id: "review-001",
    kind: "TOPIC_PATCH",
    proposalKind: "TOPIC_PATCH",
    title: "把高频使用的旧 claim 送入重审",
    summary: "主题「Inkvault repositioning」里有 1 条高频使用的 claim 需要重新复核。",
    sourceId: "source-005",
    sourceTitle: "Wiki memory compilation notes",
    targetTopicId: "topic-001",
    targetTopicTitle: "Inkvault repositioning",
    proposedTopicTitle: null,
    proposedUnderstanding: "补一轮更新证据，再决定是否调整当前理解。",
    proposedOpenQuestions:
      "这条高频 claim 是否还成立，需要补哪条更新来源？；为什么「AI 生成的知识必须先进入 ingest 队列。」最近被频繁使用却还没有完成新一轮复核？",
    proposedClaim: "AI 生成的知识必须先进入 ingest 队列。",
    proposedVaultPath: "wiki/inkvault-repositioning.md",
    sourceVaultPath: "raw/2026-04-13-topic-memory-compilation-notes.md",
    proposalPayload: {
      topicDecision: {
        decision: "PATCH",
        targetTopicId: "topic-001",
        targetTopicTitle: "Inkvault repositioning",
        proposedTopicTitle: null
      },
      summaryChanges: ["针对高频使用但久未复核的 claim，补一轮更新证据并重审当前理解。"],
      claims: [
        {
          statement: "AI 生成的知识必须先进入 ingest 队列。",
          citationLabel: "Wiki memory compilation notes",
          sourceId: "source-005",
          citationChunkIds: [],
          supportingChunkIds: [],
          evidenceCount: 0,
          provenanceStatus: "unsupported",
          lastVerifiedAt: "2026-04-13T08:30:00Z",
          usageCount: 4,
          lastUsedAt: "2026-05-04T03:00:00Z",
          needsReview: true,
          hasConflict: true
        }
        ],
      conflicts: ["「AI 生成的知识必须先进入 ingest 队列。」与同主题里的另一条判断当前彼此冲突，需要统一裁决。"],
      openQuestions: [
        "这条高频 claim 是否还成立，需要补哪条更新来源？",
        "为什么「AI 生成的知识必须先进入 ingest 队列。」最近被频繁使用却还没有完成新一轮复核？"
      ],
      explanation: "这些 claim 最近仍在 Ask 中被调用，但验证时间过旧或证据仍偏弱，建议先进入 ingest 复核再决定是否更新 wiki。",
      evidence: [
        {
          sourceId: "source-005",
          sourceTitle: "Wiki memory compilation notes",
          sourceVaultPath: "raw/2026-04-13-topic-memory-compilation-notes.md",
          locator: "file:///research/topic-memory.pdf",
          excerpt: "补充说明 canonical knowledge 必须经过 review 才能进入 wiki。"
        }
      ]
    },
    createdAt: "2026-04-13T08:10:00Z"
  },
  {
    id: "review-002",
    kind: "TOPIC_CREATE",
    proposalKind: "TOPIC_CREATE",
    title: "从 raw 建立 wiki 页面",
    summary: "Today Vault Panel 需要独立 wiki 页面继续沉淀。",
    sourceId: "source-002",
    sourceTitle: "为什么 Today Vault Panel 应成为登录后的第一屏",
    targetTopicId: null,
    targetTopicTitle: null,
    proposedTopicTitle: "Today Vault Panel",
    proposedUnderstanding: "首页应先呈现 LLM Wiki，而不是旧式工作台摘要。",
    proposedOpenQuestions: "哪些首页信息应固定在 Today Vault Panel？",
    proposedClaim: "首页应先呈现 LLM Wiki。",
    proposedVaultPath: "wiki/today-vault-panel.md",
    sourceVaultPath: "raw/2026-04-12-today-vault-panel.md",
    proposalPayload: {
      topicDecision: {
        decision: "CREATE",
        targetTopicId: null,
        targetTopicTitle: null,
        proposedTopicTitle: "Today Vault Panel"
      },
      summaryChanges: ["新建一个聚焦首页形态的 wiki 页面，并沉淀首页为何要以研究工作流为中心。"],
      claims: [
        {
          statement: "首页应先呈现 LLM Wiki。",
          citationLabel: "为什么 Today Vault Panel 应成为登录后的第一屏",
          sourceId: "source-002",
          citationChunkIds: ["chunk-source-002"],
          supportingChunkIds: [],
        evidenceCount: 1,
        provenanceStatus: "partial",
        hasConflict: false
      }
      ],
      conflicts: [],
      openQuestions: ["哪些首页信息应固定在 Today Vault Panel？"],
      explanation: "系统建议新建主题，因为这份 raw 讨论的是首页形态，不适合直接并到现有产品定位页里。",
      evidence: [
        {
          sourceId: "source-002",
          sourceTitle: "为什么 Today Vault Panel 应成为登录后的第一屏",
          sourceVaultPath: "raw/2026-04-12-today-vault-panel.md",
          locator: "legacy://note-002",
          excerpt: "迁移材料强调首页先看到研究驾驶舱，而不是旧式文档列表。"
        }
      ]
    },
    createdAt: "2026-04-12T07:42:00Z"
  },
  {
    id: "review-003",
    kind: "TOPIC_CREATE",
    proposalKind: "TOPIC_CREATE",
    title: "从 raw 建立 wiki 页面",
    summary: "迁移材料强调 AI 编译必须先经过 ingest 人工确认。",
    sourceId: "source-003",
    sourceTitle: "ingest 队列如何保证 AI 编译可控",
    targetTopicId: null,
    targetTopicTitle: null,
    proposedTopicTitle: "Ingest queue discipline",
    proposedUnderstanding: "AI 生成的知识必须先进入 ingest 队列，不能直接写入 wiki。",
    proposedOpenQuestions: "哪些提案类型必须强制人工确认？",
    proposedClaim: "AI 生成的知识必须先进入 ingest 队列。",
    proposedVaultPath: "wiki/ingest-queue-discipline.md",
    sourceVaultPath: "raw/2026-04-12-ingest-review-discipline.md",
    proposalPayload: {
      topicDecision: {
        decision: "CREATE",
        targetTopicId: null,
        targetTopicTitle: null,
        proposedTopicTitle: "Ingest queue discipline"
      },
      summaryChanges: ["沉淀一页专门解释 ingest 人工确认纪律，避免 agent 静默改写知识库。"],
      claims: [
        {
          statement: "AI 生成的知识必须先进入 ingest 队列。",
          citationLabel: "ingest 队列如何保证 AI 编译可控",
          sourceId: "source-003",
          citationChunkIds: [],
          supportingChunkIds: [],
        evidenceCount: 0,
        provenanceStatus: "unsupported",
        hasConflict: false
      }
      ],
      conflicts: [],
      openQuestions: ["哪些提案类型必须强制人工确认？"],
      explanation: "系统建议单独建页，因为这份 raw 讨论的是 agent 纪律和产品约束，本身已经形成一个独立研究主题。",
      evidence: [
        {
          sourceId: "source-003",
          sourceTitle: "ingest 队列如何保证 AI 编译可控",
          sourceVaultPath: "raw/2026-04-12-ingest-review-discipline.md",
          locator: "legacy://note-003",
          excerpt: "迁移材料指出 AI 编译必须经过 ingest 才能进入 wiki 记忆。"
        }
      ]
    },
    createdAt: "2026-04-12T06:58:00Z"
  }
];

export const researchTopicDetailsFixture: ResearchTopicDetail[] = [
  {
    id: "topic-001",
    title: "Inkvault repositioning",
    summary: "把产品中心收回到 raw / ingest / wiki，由 raw 驱动、由 ingest 把关。",
    vaultPath: "wiki/inkvault-repositioning.md",
    contentHash: "mock-wiki-inkvault",
    currentUnderstanding: [
      "wiki 是新的核心对象，Note 退回为待迁移 raw。",
      "AI 只提交 ingest 补丁提案，不直接改写 wiki 事实。"
    ],
    openQuestions: [
      "迁移老笔记时，哪些内容应进入 wiki？",
      "什么时候才需要恢复更丰富的公开阅读层？"
    ],
    sources: [
      {
        sourceId: "source-004",
        title: "Research-first wiki note",
        kind: "WEB",
        locator: "https://example.com/wiki",
        vaultPath: "raw/2026-04-13-research-first-wiki-note.md",
        legacyNoteId: null
      },
      {
        sourceId: "source-005",
        title: "Wiki memory compilation notes",
        kind: "PDF",
        locator: "file:///research/topic-memory.pdf",
        vaultPath: "raw/2026-04-13-topic-memory-compilation-notes.md",
        legacyNoteId: null
      },
      {
        sourceId: "source-001",
        title: "将 Inkvault 重定位为私有研究型 LLM Wiki",
        kind: "LEGACY_NOTE",
        locator: "legacy://note-001",
        vaultPath: "raw/2026-04-12-inkvault-llm-wiki.md",
        legacyNoteId: "note-001"
      }
    ],
    keyClaims: [
      {
        id: "claim-001",
        statement: "wiki 取代 Note 成为产品主对象。",
        sourceId: "source-004",
        citationLabel: "Research-first wiki note",
        evidenceCount: 1,
        provenanceStatus: "supported",
        lastVerifiedAt: "2026-05-10T08:30:00Z",
        usageCount: 3,
        lastUsedAt: "2026-05-03T03:00:00Z",
        needsReview: false,
        hasConflict: false
      },
      {
        id: "claim-002",
        statement: "AI 生成的知识必须先进入 ingest 队列。",
        sourceId: "source-005",
        citationLabel: "Wiki memory compilation notes",
        evidenceCount: 0,
        provenanceStatus: "unsupported",
        lastVerifiedAt: "2026-04-13T08:30:00Z",
        usageCount: 4,
        lastUsedAt: "2026-05-04T03:00:00Z",
        needsReview: true,
        hasConflict: true
      }
    ],
    thread: [
      {
        id: "thread-001",
        role: "SYSTEM",
        content: "已从迁移材料生成这个 wiki 的第一版理解。",
        sourceId: "source-001",
        createdAt: "2026-04-12T08:15:00Z"
      },
      {
        id: "thread-002",
        role: "ASSISTANT",
        content: "已把新 raw 编译进当前 wiki。",
        sourceId: "source-004",
        createdAt: "2026-04-13T08:30:00Z"
      }
    ],
    updatedAt: "2026-04-13T08:30:00Z"
  },
  {
    id: "topic-002",
    title: "Today Vault Panel",
    summary: "首页应该先给出 raw、ingest 和 wiki 上下文，而不是旧的笔记或计划列表。",
    vaultPath: "wiki/today-vault-panel.md",
    contentHash: "mock-wiki-panel",
    currentUnderstanding: ["Today Vault Panel 应成为进入系统后的第一屏。"],
    openQuestions: ["raw、ingest、Ask 之间最短路径如何呈现？"],
    sources: [
      {
        sourceId: "source-002",
        title: "为什么 Today Vault Panel 应成为登录后的第一屏",
        kind: "LEGACY_NOTE",
        locator: "legacy://note-002",
        vaultPath: "raw/2026-04-12-today-vault-panel.md",
        legacyNoteId: "note-002"
      }
    ],
    keyClaims: [
      {
        id: "claim-003",
        statement: "首页应先呈现 LLM Wiki。",
        sourceId: "source-002",
        citationLabel: "为什么 Today Vault Panel 应成为登录后的第一屏",
        evidenceCount: 1,
        provenanceStatus: "partial",
        lastVerifiedAt: "2026-05-09T11:20:00Z",
        usageCount: 1,
        lastUsedAt: "2026-05-01T11:20:00Z",
        needsReview: false,
        hasConflict: false
      }
    ],
    thread: [
      {
        id: "thread-003",
        role: "SYSTEM",
        content: "已为 Vault-first 首页建立独立 wiki。",
        sourceId: "source-002",
        createdAt: "2026-04-12T07:50:00Z"
      }
    ],
    updatedAt: "2026-04-12T11:20:00Z"
  }
];

export const researchDashboardFixture: ResearchDashboard = {
  summary: {
    activeTopics: researchTopicSummariesFixture.length,
    pendingReviews: researchReviewItemsFixture.length,
    inboxSources: researchSourcesFixture.filter((source) => source.status === "RAW" || source.status === "INGEST_PENDING").length,
    totalSources: researchSourcesFixture.length
  },
  health: {
    rawBacklogCount: researchSourcesFixture.filter((source) => source.status === "RAW" || source.status === "INGEST_PENDING").length,
    reviewBacklogCount: researchReviewItemsFixture.length,
    openQuestionCount: researchTopicSummariesFixture.reduce((total, topic) => total + topic.openQuestionCount, 0),
    knowledgeGapCount: 1,
    writebackCandidateCount: 1,
    unsupportedClaimCount: 1,
    staleClaimCount: 1,
    conflictingClaimCount: 2,
    signals: [
      {
        type: "RAW_BACKLOG",
        severity: "warning",
        title: "raw 里有 3 条材料等待编译",
        summary: "这些来源还停在 raw / ingest 前半段，需要通过 ingest 判断是否进入 wiki。",
        relatedId: "source-004",
        relatedTitle: "Research-first wiki note"
      },
      {
        type: "REVIEW_BACKLOG",
        severity: "warning",
        title: "ingest 队列有 3 条待审阅提案",
        summary: "这些 AI 编译结果还没有被接受或忽略，wiki 的长期记忆仍未更新。",
        relatedId: "review-001",
        relatedTitle: "把 raw 补充进现有 wiki"
      },
      {
        type: "OPEN_QUESTIONS",
        severity: "info",
        title: "wiki 里还有 3 个开放问题",
        summary: "开放问题是下一轮 Ask、补 raw 或审 ingest 的优先线索。",
        relatedId: "topic-001",
        relatedTitle: "Inkvault repositioning"
      },
      {
        type: "UNSUPPORTED_CLAIM",
        severity: "warning",
        title: "有 1 条 claim 缺少直接证据",
        summary: "至少有一条关键结论还没有直接证据链支持，建议回到 wiki、raw 或 ingest 补证。",
        relatedId: "topic-001",
        relatedTitle: "Inkvault repositioning"
      },
      {
        type: "STALE_CLAIM",
        severity: "warning",
        title: "有 1 条常用 claim 需要重审",
        summary: "这条 claim 最近仍被 Ask 使用，但验证时间过旧或证据仍偏弱，建议进入 ingest 复核。",
        relatedId: "topic-001",
        relatedTitle: "Inkvault repositioning"
      },
      {
        type: "CONFLICTING_CLAIM",
        severity: "warning",
        title: "有 2 条 claim 彼此冲突",
        summary: "同一主题里出现了方向相反的 claim，建议先回到 ingest 做一轮统一裁决。",
        relatedId: "topic-001",
        relatedTitle: "Inkvault repositioning"
      },
      {
        type: "KNOWLEDGE_GAP",
        severity: "warning",
        title: "Ask 最近发现 1 个知识缺口",
        summary: "当前 wiki 还没有覆盖更细的外部资料。",
        relatedId: "ask-topic-001",
        relatedTitle: "这个主题当前最稳定的理解是什么？"
      },
      {
        type: "WRITEBACK_CANDIDATE",
        severity: "info",
        title: "有 1 条 Ask 回答可沉淀回 wiki",
        summary: "这些回答已标记为可写回，但还没有明显进入 ingest 审阅队列。",
        relatedId: "ask-topic-001",
        relatedTitle: "这个主题当前最稳定的理解是什么？"
      }
    ]
  },
  focusTopic: researchTopicSummariesFixture[0] ?? null,
  recentSources: researchSourcesFixture.slice(0, 3),
  pendingReviews: researchReviewItemsFixture,
  suggestedQuestions: [
    "raw 和 wiki 的边界是什么？",
    "当前最值得先审阅哪条迁移提案？",
    "哪些 raw 已经足够稳定，可以沉淀进现有 wiki？"
  ]
};

export const researchAskHistoryFixture: ResearchAskHistoryEntry[] = [
  {
    id: "ask-topic-001",
    title: "这个主题当前最稳定的理解是什么？",
    href: "/app/ask?q=%E8%BF%99%E4%B8%AA%E4%B8%BB%E9%A2%98%E5%BD%93%E5%89%8D%E6%9C%80%E7%A8%B3%E5%AE%9A%E7%9A%84%E7%90%86%E8%A7%A3%E6%98%AF%E4%BB%80%E4%B9%88%EF%BC%9F&topicId=topic-001",
    topicTitle: "Inkvault repositioning",
    preview: "当前最稳定的理解是 wiki 是新的核心对象。",
    updatedAt: "2026-05-03T03:00:00Z"
  }
];

export const workspaceAskBriefingFixture: ResearchAskBriefing = {
  scope: "workspace",
  topicId: null,
  topicTitle: null,
  askTurnId: null,
  summary: "当前最需要先看清证据缺口，再决定是继续追问、补 raw，还是先处理 ingest 积压。",
  confidence: 0.74,
  knowledgeGaps: [
    {
      title: "raw 里有 3 条材料等待编译",
      detail: "这些来源还停在 raw / ingest 前半段，还没有进入可长期复用的知识层。",
      href: "/app/raw"
    },
    {
      title: "ingest 队列有 3 条待审阅提案",
      detail: "这些 AI 编译结果还没有被人工确认，wiki 的长期记忆仍未更新。",
      href: "/app/ingest"
    },
    {
      title: "有 1 条 claim 缺少直接证据",
      detail: "当前已有结论进入 wiki，但至少有一条关键判断还没有直接证据链支撑。",
      href: "/app/wiki/topic-001"
    },
    {
      title: "有 1 条常用 claim 需要重审",
      detail: "这条 claim 最近仍被 Ask 使用，但验证时间过旧或证据仍偏弱，最好先进入 ingest 做一轮复核。",
      href: "/app/ingest"
    },
    {
      title: "有 2 条 claim 彼此冲突",
      detail: "同一主题里已经出现方向相反的 claim，继续推进前最好先进入 ingest 统一裁决。",
      href: "/app/ingest"
    }
  ],
  nextActions: [
    {
      kind: "CONTINUE_ASK",
      label: "继续追问",
      description: "先围绕当前焦点主题缩小问题范围，确认最值得补的证据。",
      href: "/app"
    },
    {
      kind: "OPEN_INGEST",
      label: "打开审阅队列",
      description: "先处理最靠前的提案，再继续扩展知识层。",
      href: "/app/ingest"
    },
    {
      kind: "OPEN_RAW",
      label: "打开 raw",
      description: "检查哪些材料还停在原始资料层，尚未进入 ingest。",
      href: "/app/raw"
    }
  ],
  suggestedQuestions: [
    "当前哪条提案最值得先审阅？",
    "围绕「Inkvault repositioning」还缺哪条证据？",
    "哪些 raw 已经足够稳定，可以沉淀进现有 wiki？"
  ],
  supportingSignals: [
    {
      type: "RAW_BACKLOG",
      title: "raw 里有 3 条材料等待编译",
      summary: "这些来源还停在 raw / ingest 前半段，需要通过 ingest 判断是否进入 wiki。",
      href: "/app/raw"
    },
    {
      type: "REVIEW_BACKLOG",
      title: "ingest 队列有 3 条待审阅提案",
      summary: "这些 AI 编译结果还没有被接受或忽略，wiki 的长期记忆仍未更新。",
      href: "/app/ingest"
    },
    {
      type: "UNSUPPORTED_CLAIM",
      title: "有 1 条 claim 缺少直接证据",
      summary: "至少有一条关键结论还没有直接证据链支持，建议先补证再沉淀更多判断。",
      href: "/app/wiki/topic-001"
    },
    {
      type: "STALE_CLAIM",
      title: "有 1 条常用 claim 需要重审",
      summary: "这条高频 claim 最近仍被 Ask 使用，但验证时间过旧或证据仍偏弱。",
      href: "/app/ingest"
    },
    {
      type: "CONFLICTING_CLAIM",
      title: "有 2 条 claim 彼此冲突",
      summary: "同一主题里出现了方向相反的 claim，建议先回到 ingest 做一轮统一裁决。",
      href: "/app/ingest"
    }
  ],
  generatedAt: "2026-05-11T09:00:00Z"
};

export const askTurnAskBriefingFixture: ResearchAskBriefing = {
  scope: "ask_turn",
  topicId: "topic-001",
  topicTitle: "Inkvault repositioning",
  askTurnId: "ask-topic-001",
  summary: "这轮问答已经给出一版可继续推进的判断，但仍缺少更扎实的外部证据来收口。",
  confidence: 0.86,
  knowledgeGaps: [
    {
      title: "当前 wiki 还没有覆盖更细的外部资料。",
      detail: "如果要把回答沉淀成更稳的长期理解，下一步仍需要补一条更直接的外部佐证。",
      href: "/app"
    },
    {
      title: "有 1 条 claim 缺少直接证据",
      detail: "当前主题里至少有一条关键结论还处在 unsupported 状态，继续追问前最好先确认它的证据链。",
      href: "/app/wiki/topic-001"
    },
    {
      title: "有 1 条常用 claim 需要重审",
      detail: "这条 claim 最近仍被 Ask 使用，但验证时间过旧或证据仍偏弱，下一步更适合先送进 ingest 复核。",
      href: "/app/ingest"
    },
    {
      title: "有 2 条 claim 彼此冲突",
      detail: "同一主题里已经出现方向相反的 claim，继续沉淀前最好先统一裁决。",
      href: "/app/ingest"
    }
  ],
  nextActions: [
    {
      kind: "CONTINUE_ASK",
      label: "继续追问",
      description: "围绕这轮回答继续补证或缩小范围。",
      href: "/app"
    },
    {
      kind: "WRITEBACK",
      label: "沉淀到知识库",
      description: "把这轮回答送入 ingest 审阅，而不是直接改写 wiki。",
      href: "/app"
    },
    {
      kind: "OPEN_INGEST",
      label: "发起 claim 重审",
      description: "这些高频 claim 需要回到 ingest 做一轮复核，避免继续带着旧判断推进。",
      href: "/app/ingest"
    },
    {
      kind: "OPEN_INGEST",
      label: "处理 claim 冲突",
      description: "回到 ingest 统一裁决互相打架的 claim，避免继续带着冲突理解推进。",
      href: "/app/ingest"
    }
  ],
  suggestedQuestions: ["如果继续联网补料，最需要验证哪条外部论据？"],
  supportingSignals: [
    {
      type: "KNOWLEDGE_GAP",
      title: "Ask 最近发现 1 个知识缺口",
      summary: "当前 wiki 还没有覆盖更细的外部资料。",
      href: "/app/wiki"
    },
    {
      type: "UNSUPPORTED_CLAIM",
      title: "有 1 条 claim 缺少直接证据",
      summary: "当前主题里至少有一条关键结论还没有直接证据链支撑。",
      href: "/app/wiki/topic-001"
    },
    {
      type: "STALE_CLAIM",
      title: "有 1 条常用 claim 需要重审",
      summary: "这条高频 claim 最近仍被 Ask 使用，但验证时间过旧或证据仍偏弱。",
      href: "/app/ingest"
    },
    {
      type: "CONFLICTING_CLAIM",
      title: "有 2 条 claim 彼此冲突",
      summary: "同一主题里出现了方向相反的 claim，建议先回到 ingest 做一轮统一裁决。",
      href: "/app/ingest"
    }
  ],
  generatedAt: "2026-05-11T09:05:00Z"
};

export function getResearchTopicDetailFixture(id: string) {
  return researchTopicDetailsFixture.find((topic) => topic.id === id);
}

export function answerResearchQuestionFixture(request: ResearchAskRequest): ResearchAskResponse {
  const topic = request.topicId ? getResearchTopicDetailFixture(request.topicId) : undefined;
  const mode = request.mode === "vault_plus_web" ? "vault_plus_web" : "vault";

  if (!topic) {
    return {
      id: "ask-global-001",
      topicId: null,
      parentAskTurnId: null,
      threadRootAskTurnId: "ask-global-001",
      lineageAskTurnIds: ["ask-global-001"],
      question: request.question,
      answer:
        mode === "vault_plus_web"
          ? "当前最需要先处理的是 ingest 队列，其次再把新 raw 来源并入现有 wiki；如果要继续验证外部趋势，下一步应显式联网补料。"
          : "当前最需要先处理的是 ingest 队列，其次再把新 raw 来源并入现有 wiki。",
      confidence: mode === "vault_plus_web" ? 0.68 : 0.74,
      retrievalMode: "lexical_fallback",
      usedChunkIds: ["chunk-source-004", "chunk-source-002"],
      followUpQuestions: ["当前哪条 ingest 提案最值得优先审阅？"],
      knowledgeGaps: mode === "vault_plus_web" ? ["现有 vault 缺少最新外部资料，仍需要显式联网补料。"] : [],
      usedWikiIds: [],
      usedSourceIds: researchSourcesFixture.slice(0, 2).map((source) => source.id),
      usedWebSources:
        mode === "vault_plus_web"
          ? [
              {
                url: "https://example.com/research/ingest-priority",
                title: "Ingest priority research note",
                excerpt: "外部资料建议先梳理 ingest 队列，再处理知识沉淀。",
                reasonUsed: "用于补足 vault 里还没有覆盖的外部优先级判断。"
              }
            ]
          : [],
      contextAskTurnIds: request.continueFromAskTurnId ? [request.continueFromAskTurnId] : [],
      canWriteback: true,
      citations: researchSourcesFixture.slice(0, 2).map((source) => ({
        sourceId: source.id,
        title: source.title,
        kind: source.kind,
        locator: source.locator,
        vaultPath: source.vaultPath
      })),
      createdAt: "2026-04-13T09:00:00Z"
    };
  }

  return {
    id: "ask-topic-001",
    topicId: topic.id,
    parentAskTurnId: request.continueFromAskTurnId ?? null,
    threadRootAskTurnId: request.continueFromAskTurnId ?? "ask-topic-001",
    lineageAskTurnIds: request.continueFromAskTurnId ? [request.continueFromAskTurnId, "ask-topic-001"] : ["ask-topic-001"],
    question: request.question,
    answer: `当前最稳定的理解是 ${topic.currentUnderstanding[0]} 同时仍需要追问：${topic.openQuestions[0]}`,
    confidence: mode === "vault_plus_web" ? 0.79 : 0.86,
    retrievalMode: "lexical_fallback",
    usedChunkIds: ["chunk-topic-001", "chunk-source-004"],
    followUpQuestions: [
      mode === "vault_plus_web" ? "如果继续联网补料，最需要验证哪条外部论据？" : "这个主题下一轮最值得补哪条证据？"
    ],
    knowledgeGaps: mode === "vault_plus_web" ? ["当前 wiki 还没有覆盖更细的外部资料。"] : [],
    usedWikiIds: [topic.id],
    usedSourceIds: topic.sources.slice(0, 2).map((source) => source.sourceId),
    usedWebSources:
      mode === "vault_plus_web"
        ? [
            {
              url: "https://example.com/research/topic-first",
              title: "Topic-first workflow review",
              excerpt: "外部评述同样支持 Topic-first 的研究工作流。",
              reasonUsed: "用于补足当前主题在 vault 外的佐证。"
            }
          ]
        : [],
    contextAskTurnIds: request.continueFromAskTurnId ? [request.continueFromAskTurnId] : [],
    canWriteback: true,
    citations: topic.sources.slice(0, 2).map((source) => ({
      sourceId: source.sourceId,
      title: source.title,
      kind: source.kind,
      locator: source.locator,
      vaultPath: source.vaultPath
    })),
    createdAt: "2026-04-13T09:05:00Z"
  };
}

export function getAskBriefingFixture(input?: { topicId?: string; askTurnId?: string }) {
  if (input?.askTurnId) {
    return {
      ...askTurnAskBriefingFixture,
      askTurnId: input.askTurnId
    };
  }

  if (input?.topicId) {
    return {
      ...workspaceAskBriefingFixture,
      scope: "topic" as const,
      topicId: input.topicId,
      topicTitle: getResearchTopicDetailFixture(input.topicId)?.title ?? "未命名主题",
      summary: `当前主题「${getResearchTopicDetailFixture(input.topicId)?.title ?? "未命名主题"}」最需要先补证再推进。`
    };
  }

  return workspaceAskBriefingFixture;
}

export function createAskWritebackFixture(askTurnId: string): ResearchReviewItem {
  return {
    ...researchReviewItemsFixture[0],
    id: `review-from-${askTurnId}`,
    title: "把 Ask 结论补充进现有 wiki",
    summary: "把“这个主题当前最稳定的理解是什么？”的回答沉淀进 Inkvault repositioning。",
    proposedUnderstanding: "当前最稳定的理解是 wiki 是新的核心对象，Note 退回为待迁移 raw。 同时仍需要追问：迁移老笔记时，哪些内容应进入 wiki？",
    proposedOpenQuestions: "这个主题当前最稳定的理解是什么？",
    proposedClaim: "当前最稳定的理解是 wiki 是新的核心对象，Note 退回为待迁移 raw。",
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
          statement: "当前最稳定的理解是 wiki 是新的核心对象，Note 退回为待迁移 raw。",
          citationLabel: "Research-first wiki note",
          sourceId: "source-004",
          citationChunkIds: ["chunk-source-004"],
          supportingChunkIds: ["chunk-source-004"],
          evidenceCount: 1,
          provenanceStatus: "supported"
        }
      ],
      conflicts: [],
      openQuestions: ["这个主题当前最稳定的理解是什么？"],
      explanation: "系统建议把这次 Ask 当前回答补充进现有主题「Inkvault repositioning」，因为当前答案已经命中了这个 wiki 页面。",
      evidence: [
        {
          sourceId: "source-004",
          sourceTitle: "Research-first wiki note",
          sourceVaultPath: "raw/2026-04-13-research-first-wiki-note.md",
          locator: "https://example.com/wiki",
          excerpt: "强调 wiki-first 的研究工作流。"
        }
      ]
    }
  };
}
