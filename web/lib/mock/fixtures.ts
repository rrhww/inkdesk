import type {
  AgentSuggestion,
  AuthorProfile,
  KnowledgeNoteDetail,
  PlanDetail,
  PublicArticleDetail,
  PublicKnowledgeBucket,
  PublicProject,
  PublicUpdateItem,
  QuickAction,
  SettingsRecord,
  TagRecord
} from "@/lib/types";

export const authorProfileFixture: AuthorProfile = {
  name: "R",
  title: "做项目，也整理开发学习笔记的人",
  summary: "这里公开我正在推进的项目、分门别类的开发学习笔记，以及那些最后沉淀成方法的工作判断。",
  intro: "我把公开侧当成一张长期维护的知识地图。它既展示我正在构建的项目，也整理我在开发技术、计算机基础、项目实践和方法思考上的笔记索引。",
  manifesto: "我相信个人系统不该只是存文档，而应该帮助人持续思考、推进项目、组织行动。",
  focusAreas: ["开发技术", "计算机基础", "项目实践", "方法与思考"],
  researchStatement:
    "这里不追求高频更新，而是持续整理那些值得反复返回的项目经验、学习记录与方法线索。",
  workingNote: "我更在意内容之间能不能互相指路，而不是把页面做成一次性看完的作品集。",
  contactLinks: [
    { label: "Email", href: "mailto:r@inkdesk.local" },
    { label: "GitHub", href: "https://github.com/inkdesk" },
    { label: "最近文章", href: "/articles/super-personal-workbench-reframe" }
  ]
};

export const publicProjectsFixture: PublicProject[] = [
  {
    slug: "inkdesk-main-system",
    title: "Inkdesk 主系统",
    summary: "把笔记、任务与 Agent 编排到同一工作台里，让公开输出和私有工作都能长期运转。",
    kind: "精选项目",
    status: "active",
    statusLabel: "持续构建中",
    updatedAt: "2026-04-15 21:10",
    primaryHref: "https://github.com/inkdesk",
    repoHref: "https://github.com/inkdesk",
    stack: ["Next.js", "TypeScript", "Agent Workflow", "Content System"],
    highlights: [
      "把公开展示层与主系统工作台明确拆开",
      "让笔记、任务计划与检索入口围绕真实工作组织",
      "持续把方法沉淀成可公开浏览的文章与索引"
    ],
    relatedArticleSlugs: ["super-personal-workbench-reframe", "public-home-as-knowledge-map"],
    relatedBucketSlugs: ["project-practice", "methods-thinking"]
  },
  {
    slug: "developer-notes-atlas",
    title: "开发笔记图谱",
    summary: "把技术学习和项目复盘做成一张可持续扩展的公开索引，而不是散落的文章流。",
    kind: "在建索引",
    status: "building",
    statusLabel: "正在搭架子",
    updatedAt: "2026-04-14 19:40",
    primaryHref: "https://github.com/inkdesk",
    repoHref: "https://github.com/inkdesk",
    stack: ["Taxonomy", "Writing Workflow", "Curation"],
    highlights: [
      "一级宽分类配合二级专题，兼顾清晰与扩展性",
      "让文章、项目与方法相互关联，而不是孤立陈列",
      "优先为长期浏览设计，而不是短期更新频率设计"
    ],
    relatedArticleSlugs: ["frontend-layering-for-backoffice", "study-notes-need-a-maintained-index"],
    relatedBucketSlugs: ["development-tech", "methods-thinking"]
  },
  {
    slug: "systems-thinking-notebook",
    title: "系统化学习手册",
    summary: "把计网、操作系统、数据库这些基础知识整理成能回看、能串联项目的问题地图。",
    kind: "长期积累",
    status: "stable",
    statusLabel: "持续整理",
    updatedAt: "2026-04-13 22:00",
    primaryHref: "https://github.com/inkdesk",
    repoHref: "https://github.com/inkdesk",
    stack: ["Networking", "OS", "Database", "Learning Notes"],
    highlights: [
      "围绕真实问题组织基础知识，而不是只记概念",
      "把底层原理和工程判断连接起来",
      "给后续项目实践提供稳定的知识回路"
    ],
    relatedArticleSlugs: ["one-request-through-network-stack", "why-indexes-change-query-cost"],
    relatedBucketSlugs: ["computer-fundamentals", "project-practice"]
  }
];

export const publicArticleFixtures: PublicArticleDetail[] = [
  {
    id: "pub-001",
    slug: "frontend-layering-for-backoffice",
    title: "给中后台页面做一次真正可维护的前端分层",
    excerpt: "从模块边界、状态职责和页面骨架入手，把“能跑”变成“能持续维护”。",
    folder: "开发技术",
    updatedAt: "2026-04-15 18:30",
    readingMinutes: 6,
    tags: ["前端", "分层", "工程化"],
    sourceNoteId: "note-001",
    body: [
      "很多中后台页面的问题不在于功能太多，而在于功能都黏在同一层里。组件、数据请求和页面状态一旦长在一起，后续任何修改都会牵一片。",
      "我现在更倾向于先拆出页面骨架、领域块和共享状态，再决定哪些逻辑真的值得抽离。这样做的好处不是优雅，而是每次迭代都更容易找到落点。",
      "当页面开始服务长期项目时，可维护性本身就是体验的一部分。"
    ],
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: ["note-001", "note-003"]
  },
  {
    id: "pub-002",
    slug: "one-request-through-network-stack",
    title: "从一次请求回看网络栈到底发生了什么",
    excerpt: "把 DNS、TCP、HTTP 和浏览器处理链路放回同一个时间轴里看，很多模糊点会突然清楚。",
    folder: "计算机基础",
    updatedAt: "2026-04-15 09:20",
    readingMinutes: 7,
    tags: ["计网", "HTTP", "TCP"],
    sourceNoteId: "note-003",
    body: [
      "如果只分别去背 DNS、TCP、HTTP，它们会一直像三门独立课程。但当我把它们放回一次真实请求里，就能看到每一步到底在为后面哪一步服务。",
      "网络基础最容易变成碎片化记忆，所以我更喜欢用“发生顺序”来重建它。这样在排查问题或读接口日志时，会更容易想到系统真正卡在哪里。",
      "理解顺序，比记住术语更能帮我在项目里做判断。"
    ],
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: ["note-003"]
  },
  {
    id: "pub-003",
    slug: "super-personal-workbench-reframe",
    title: "把 Inkdesk 从知识库改造成真正的个人工作台",
    excerpt: "这次重构的关键不是多做一个模块，而是重新安排“知识、行动、公开展示”三者的关系。",
    folder: "项目实践",
    updatedAt: "2026-04-15 21:00",
    readingMinutes: 5,
    tags: ["项目实践", "系统设计", "Inkdesk"],
    sourceNoteId: "note-001",
    body: [
      "我不再把 Inkdesk 理解成一个单纯的知识库，而是一个围绕长期项目运转的个人工作台。公开展示层负责被别人浏览，私有工作台负责帮我继续推进。",
      "真正的变化不是功能增减，而是信息架构被重新排过。项目、笔记、Agent 和计划不再平铺并列，而是围绕“下一步要推进什么”来组织。",
      "当公开输出也开始服务项目而不是只服务发布，展示页本身就会更有生命力。"
    ],
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: ["note-001", "note-002", "note-003"]
  },
  {
    id: "pub-004",
    slug: "study-notes-need-a-maintained-index",
    title: "学习笔记需要的不是更多，而是一张可维护的索引",
    excerpt: "当笔记开始跨主题生长时，分类方式本身就变成了一种长期维护工作。",
    folder: "方法与思考",
    updatedAt: "2026-04-14 22:10",
    readingMinutes: 4,
    tags: ["学习方法", "索引", "知识管理"],
    sourceNoteId: "note-003",
    body: [
      "笔记越多，越不能只靠搜索和时间顺序。真正有用的是一张能不断修订的索引，让你知道这份内容应该从哪里重新进入。",
      "所以我现在更喜欢宽分类加专题标签，而不是一开始就做非常细的层级。这样既能承接新内容，也不会让旧内容失去位置。",
      "一份好的笔记索引，不只是目录，也是重新开始学习时的入口。"
    ],
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: ["note-003"]
  },
  {
    id: "pub-005",
    slug: "why-indexes-change-query-cost",
    title: "为什么索引会直接改变一次查询的体感成本",
    excerpt: "理解数据库索引最好的方式，不是背定义，而是回到“为什么这条查询突然慢了”。",
    folder: "开发技术",
    updatedAt: "2026-04-13 20:30",
    readingMinutes: 6,
    tags: ["数据库", "索引", "查询优化"],
    sourceNoteId: "note-001",
    body: [
      "当一条查询慢下来时，索引就不再是抽象概念，而是你能不能继续推进功能的现实问题。",
      "我更喜欢从执行计划、扫描范围和排序代价去理解索引。这样每次设计表结构时，就不只是“按经验加索引”，而是知道自己在换什么。",
      "数据库里的很多判断，本质上都是在时间、空间和写入成本之间取一个平衡。"
    ],
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: ["note-001"]
  },
  {
    id: "pub-006",
    slug: "public-home-as-knowledge-map",
    title: "把公开首页做成知识地图，而不是时间流",
    excerpt: "展示页真正吸引人停留的，不只是视觉，而是让人一眼看懂这里有哪些内容值得继续逛。",
    folder: "方法与思考",
    updatedAt: "2026-04-13 17:50",
    readingMinutes: 5,
    tags: ["展示设计", "信息架构", "公开输出"],
    sourceNoteId: "note-003",
    body: [
      "如果首页只是最新文章列表，访客会默认自己在看一个普通博客。但如果首页先是一张知识地图，人会更愿意沿着分类和项目继续往下走。",
      "我开始更重视首页的指路能力，而不是只把它当成最新内容的容器。项目、笔记和方法之间的关系，被看清楚之后，页面才会更像一个被认真编排的公开空间。",
      "好的展示不是更吵，而是更有层次。"
    ],
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: ["note-003"]
  }
];

export const publicKnowledgeBucketsFixture: PublicKnowledgeBucket[] = [
  {
    slug: "development-tech",
    title: "开发技术",
    summary: "整理 Java、前端和数据库里的工程笔记，让技术判断能回到真实项目里继续使用。",
    intro: "这里收的是那些会不断被项目重新调用的技术笔记。我更关心它们如何帮助我拆模块、看链路、做性能判断，而不只是停留在概念层。",
    subtopics: ["Java", "前端", "数据库"],
    featuredArticleSlug: "frontend-layering-for-backoffice",
    relatedArticleSlugs: ["why-indexes-change-query-cost"],
    relatedProjectSlugs: ["inkdesk-main-system", "developer-notes-atlas"]
  },
  {
    slug: "computer-fundamentals",
    title: "计算机基础",
    summary: "把计网、OS 和基础原理重新压回问题现场，避免基础知识只停留在零散记忆里。",
    intro: "我不太喜欢把基础学科当成孤立题库，所以这里会把它们重新放回一次请求、一段系统行为和一次性能判断里去理解。",
    subtopics: ["计网", "OS", "基础原理"],
    featuredArticleSlug: "one-request-through-network-stack",
    relatedArticleSlugs: [],
    relatedProjectSlugs: ["systems-thinking-notebook"]
  },
  {
    slug: "project-practice",
    title: "项目实践",
    summary: "关注项目复盘、工程化和系统设计，记录一个系统是如何被持续改造出来的。",
    intro: "项目实践这部分更像公开工作台。我会把架构取舍、页面重构和系统边界调整都放在这里，方便从结果回看过程。",
    subtopics: ["项目复盘", "工程化", "系统设计"],
    featuredArticleSlug: "super-personal-workbench-reframe",
    relatedArticleSlugs: ["public-home-as-knowledge-map"],
    relatedProjectSlugs: ["inkdesk-main-system", "systems-thinking-notebook"]
  },
  {
    slug: "methods-thinking",
    title: "方法与思考",
    summary: "收纳学习方法、开发方法和个人思考，让项目和笔记背后的工作方式也能被看见。",
    intro: "这一类内容不直接对应某个技术栈，但它们决定了我如何整理笔记、如何构建展示页，以及怎样让项目长期可持续。",
    subtopics: ["学习方法", "开发方法", "个人思考"],
    featuredArticleSlug: "study-notes-need-a-maintained-index",
    relatedArticleSlugs: ["public-home-as-knowledge-map"],
    relatedProjectSlugs: ["developer-notes-atlas", "inkdesk-main-system"]
  }
];

export const publicUpdatesFixture: PublicUpdateItem[] = [
  {
    id: "update-project-inkdesk",
    type: "project",
    title: "Inkdesk 主系统",
    summary: "公开展示层与私有工作台完成拆分，首页开始转向知识地图式浏览。",
    href: "/projects/inkdesk-main-system",
    updatedAt: "2026-04-15 21:10",
    label: "项目更新"
  },
  {
    id: "update-article-workbench",
    type: "article",
    title: "把 Inkdesk 从知识库改造成真正的个人工作台",
    summary: "重新整理了知识、行动和公开展示的边界。",
    href: "/articles/super-personal-workbench-reframe",
    updatedAt: "2026-04-15 21:00",
    label: "新文章"
  },
  {
    id: "update-article-frontend",
    type: "article",
    title: "给中后台页面做一次真正可维护的前端分层",
    summary: "从页面骨架、领域块和共享状态三层重新收束前端复杂度。",
    href: "/articles/frontend-layering-for-backoffice",
    updatedAt: "2026-04-15 18:30",
    label: "分类代表"
  },
  {
    id: "update-article-network",
    type: "article",
    title: "从一次请求回看网络栈到底发生了什么",
    summary: "把计网基础重新放回真实链路里理解。",
    href: "/articles/one-request-through-network-stack",
    updatedAt: "2026-04-15 09:20",
    label: "新文章"
  },
  {
    id: "update-project-atlas",
    type: "project",
    title: "开发笔记图谱",
    summary: "一级宽分类和二级专题结构已经定下来，开始补充代表内容。",
    href: "/projects/developer-notes-atlas",
    updatedAt: "2026-04-14 19:40",
    label: "项目更新"
  },
  {
    id: "update-article-index",
    type: "article",
    title: "学习笔记需要的不是更多，而是一张可维护的索引",
    summary: "把分类方式本身当成长期维护工作来设计。",
    href: "/articles/study-notes-need-a-maintained-index",
    updatedAt: "2026-04-14 22:10",
    label: "方法笔记"
  }
];

export const agentSuggestionsFixture: AgentSuggestion[] = [
  {
    id: "agent-001",
    category: "今日建议",
    title: "把最近三篇笔记压缩成一张行动摘要",
    summary: "优先提炼最近关于 Agent、工作台与公开输出的共识，形成下一轮产品推进输入。",
    actionLabel: "生成今日摘要",
    href: "/app/search?q=Agent"
  },
  {
    id: "agent-002",
    category: "推进建议",
    title: "从当前计划里挑出最阻塞的一项",
    summary: "先把最阻塞的任务拆解成两个下一步动作，再决定是写文档、改页面还是接接口。",
    actionLabel: "查看任务与计划",
    href: "/app/plans"
  },
  {
    id: "agent-003",
    category: "知识建议",
    title: "回顾最近公开内容与私有笔记的断层",
    summary: "检查有哪些已经成熟的内部笔记值得整理后发布出去。",
    actionLabel: "打开发布模块",
    href: "/app/publish"
  }
];

export const quickActionsFixture: QuickAction[] = [
  {
    id: "quick-001",
    label: "新建知识资产",
    summary: "直接进入知识资产工作台，开始记录新的判断。",
    href: "/app/notes/new",
    icon: "edit_note"
  },
  {
    id: "quick-002",
    label: "创建计划",
    summary: "回到计划控制台，把下一步动作固定下来。",
    href: "/app/plans",
    icon: "playlist_add_check_circle"
  },
  {
    id: "quick-003",
    label: "继续检索",
    summary: "把相关上下文重新带回当前工作流。",
    href: "/app/search?q=Agent",
    icon: "travel_explore"
  },
  {
    id: "quick-004",
    label: "进入发布",
    summary: "检查哪些知识资产已经成熟到可以发布出去。",
    href: "/app/publish",
    icon: "ios_share"
  }
];

export const notesFixture: KnowledgeNoteDetail[] = [
  {
    id: "note-001",
    title: "把 Inkdesk 从知识库改造成超级个人工作台",
    excerpt: "重新定义公开输出、主系统、Agent 控制台和任务计划在整个产品中的位置。",
    body: [
      "新的 Inkdesk 不再只是个人知识库加发布站，而是一个围绕长期项目运转的个人主系统，并带有可选的公开输出层。访客看到的是公开分享内容，主人进入后得到自己的 Agent 控制台。",
      "这意味着主系统首页不该再只是最近笔记列表，而要成为帮助我判断、组织和推进工作的中枢。",
      "笔记系统仍然是底层事实来源，但它要和 Agent、任务计划一起工作，而不是单独存在。"
    ],
    tags: ["定位", "超级个人工作台", "Agent"],
    folder: "产品重构",
    updatedAt: "2026-04-12 16:10",
    readingMinutes: 5,
    words: 1120,
    published: true,
    visibility: "public",
    visibilityLabel: "已发布",
    relatedPlanIds: ["plan-001", "plan-002"],
    relatedTagIds: ["tag-positioning", "tag-agent"],
    relatedSearchTerms: ["超级个人工作台", "Agent", "公开输出"],
    knowledgeStateLabel: "已发布",
    slug: "super-personal-workbench-reframe"
  },
  {
    id: "note-002",
    title: "为什么主系统首页必须先看到 Agent",
    excerpt: "记录 Agent 控制台为何要成为主人进入系统后的第一屏，而不是笔记列表或发布页。",
    body: [
      "如果首页先看到的只是文档列表，系统会退化成存储工具。Agent 首页的作用是把知识、任务和上下文重新编排，让系统具备主动协同感。",
      "Agent 不是为了替代人，而是为了让主系统具备建议、汇总和组织下一步动作的能力。",
      "因此首页应该同时连向计划、检索和知识资产，而不是把这些能力分散在不同的孤立列表里。"
    ],
    tags: ["Agent", "首页", "系统设计"],
    folder: "主系统结构",
    updatedAt: "2026-04-12 15:42",
    readingMinutes: 4,
    words: 860,
    published: false,
    visibility: "private",
    visibilityLabel: "仅主系统",
    relatedPlanIds: ["plan-002"],
    relatedTagIds: ["tag-agent", "tag-architecture"],
    relatedSearchTerms: ["Agent", "系统设计", "首页"],
    knowledgeStateLabel: "仅主系统"
  },
  {
    id: "note-003",
    title: "公开输出页作为分享层的结构草案",
    excerpt: "公开输出层应该同时承载已发布文章、作者介绍和长期项目分享，而不是产品官网式 landing page。",
    body: [
      "公开输出层是别人理解作者与已发布内容的入口，而不是进入私有系统的入口。因此它需要克制、清晰，并且完全去掉主人入口提示。",
      "作者介绍、公开文章和项目链接这三个模块可以共同构成一个长期有效的公开输出首页。",
      "公开内容仍然要能回溯到它在主系统里的来源，但这种来源关系只服务内容可信度，不服务系统入口暴露。"
    ],
    tags: ["公开输出", "分享", "发布"],
    folder: "输出层设计",
    updatedAt: "2026-04-12 14:58",
    readingMinutes: 3,
    words: 640,
    published: true,
    visibility: "public",
    visibilityLabel: "已发布",
    relatedPlanIds: ["plan-001", "plan-003"],
    relatedTagIds: ["tag-public", "tag-publish"],
    relatedSearchTerms: ["公开输出", "发布分享", "公开文章"],
    knowledgeStateLabel: "已发布",
    slug: "public-blog-author-portal"
  }
];

export const plansFixture: PlanDetail[] = [
  {
    id: "plan-001",
    title: "收口公开输出入口与主系统边界",
    summary: "先把公开输出入口、隐藏登录入口和主系统骨架彻底分开。",
    status: "active",
    statusLabel: "进行中",
    horizon: "today",
    horizonLabel: "今天",
    priority: "critical",
    priorityLabel: "最高优先级",
    focusLabel: "系统入口",
    nextStep: "把访客入口、隐藏登录和主系统跳转链路再检查一轮。",
    nextActionLabel: "检查入口链路",
    nextActionHref: "/app/search?q=%E5%85%AC%E5%BC%80%E8%BE%93%E5%87%BA",
    relatedNoteIds: ["note-003", "note-001"],
    relatedTagIds: ["tag-public", "tag-positioning"],
    relatedSearchTerms: ["公开输出", "发布分享"],
    agentPrompt: "把主系统入口与公开输出边界压缩成一份可执行检查清单。",
    updatedAt: "2026-04-12 18:30",
    milestones: ["确认 `/` 的双路由行为", "确认公开输出不暴露主人入口", "确认 `/app/*` 权限保护稳定"]
  },
  {
    id: "plan-002",
    title: "补齐 Agent 控制台的核心模块",
    summary: "让首页真正具备上下文汇总、任务推进和知识召回三个功能面。",
    status: "active",
    statusLabel: "进行中",
    horizon: "this-week",
    horizonLabel: "本周",
    priority: "focus",
    priorityLabel: "当前主线",
    focusLabel: "Agent 首页",
    nextStep: "把 Agent 首页与任务、知识中枢之间的跳转再压缩成更短的行动路径。",
    nextActionLabel: "打开 Agent 控制台",
    nextActionHref: "/app",
    relatedNoteIds: ["note-001", "note-002"],
    relatedTagIds: ["tag-agent", "tag-architecture"],
    relatedSearchTerms: ["Agent", "系统设计"],
    agentPrompt: "从当前笔记和计划里提炼今天最值得推进的一件事。",
    updatedAt: "2026-04-12 17:56",
    milestones: ["把 Agent 建议压缩到首页第一屏", "连通计划与知识入口", "确认快速动作可达"]
  },
  {
    id: "plan-003",
    title: "让发布模块退到次级位置",
    summary: "保留公开输出能力，但不再让它主导整个平台的叙事与导航。",
    status: "queued",
    statusLabel: "待推进",
    horizon: "next",
    horizonLabel: "下一步",
    priority: "steady",
    priorityLabel: "下一轮整理",
    focusLabel: "公开输出",
    nextStep: "只保留稳定的发布与分享路径，把公开文章继续留在次级模块里。",
    nextActionLabel: "查看发布模块",
    nextActionHref: "/app/publish",
    relatedNoteIds: ["note-003"],
    relatedTagIds: ["tag-publish", "tag-public"],
    relatedSearchTerms: ["公开输出", "发布分享"],
    agentPrompt: "判断哪些知识资产已经成熟到可以发布到公开输出。",
    updatedAt: "2026-04-12 17:10",
    milestones: ["区分已发布与待发布资产", "保留公开文章预览回链", "保持发布模块为次级叙事"]
  }
];

export const tagsFixture: TagRecord[] = [
  {
    id: "tag-agent",
    label: "Agent",
    tone: "bg-ink-primarySoft text-ink-primary",
    description: "围绕 Agent 首页、协同能力和上下文组织的知识资产。",
    noteIds: ["note-001", "note-002"],
    planIds: ["plan-002"],
    articleSlugs: ["super-personal-workbench-reframe"],
    usageCount: 4
  },
  {
    id: "tag-public",
    label: "公开输出",
    tone: "bg-[#fff4ec] text-ink-tertiary",
    description: "覆盖公开输出结构、分享内容组织和访客阅读体验。",
    noteIds: ["note-003"],
    planIds: ["plan-001", "plan-003"],
    articleSlugs: ["public-blog-author-portal"],
    usageCount: 4
  },
  {
    id: "tag-positioning",
    label: "定位",
    tone: "bg-white text-ink-text",
    description: "产品定位与系统边界相关的长期主题。",
    noteIds: ["note-001"],
    planIds: ["plan-001"],
    articleSlugs: ["super-personal-workbench-reframe"],
    usageCount: 3
  },
  {
    id: "tag-publish",
    label: "发布",
    tone: "bg-white text-ink-text",
    description: "处理主系统到公开输出层的发布路径和分享策略。",
    noteIds: ["note-003"],
    planIds: ["plan-003"],
    articleSlugs: ["public-blog-author-portal"],
    usageCount: 3
  }
];

export const settingsFixture: SettingsRecord = {
  profile: {
    displayName: "R",
    publicTitle: "构建超级个人工作台的人",
    summary: "我把 Inkdesk 当成自己的长期知识与执行系统，并持续向公开输出层分享成熟内容。",
    publicLocation: "Shanghai"
  },
  workbench: {
    defaultPage: "/app",
    compactMode: false,
    showContextRibbon: true
  },
  editor: {
    defaultView: "edit",
    autoSave: true,
    publishReminder: true
  },
  publish: {
    defaultAudience: "public",
    showProvenance: true,
    highlightRecentUpdates: true
  },
  security: {
    ownerEmail: "owner@inkdesk.local",
    sessionMode: "隐藏主人入口",
    sessionDurationLabel: "8 小时"
  }
};
