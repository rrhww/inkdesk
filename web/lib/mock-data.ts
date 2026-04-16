export type NoteStatus =
  | "blank"
  | "loading"
  | "draft"
  | "saving"
  | "error"
  | "published";

export type AuthorProfile = {
  name: string;
  title: string;
  summary: string;
  intro: string;
  manifesto: string;
  focusAreas: string[];
  researchStatement?: string;
  workingNote?: string;
  contactLinks?: Array<{
    label: string;
    href: string;
  }>;
};

export type ProjectLink = {
  name: string;
  href: string;
  description: string;
  kind: string;
};

export type PublicResearchTopic = {
  slug: string;
  title: string;
  summary: string;
  purpose: string;
  featuredArticleSlug: string;
  relatedArticleSlugs: string[];
  relatedProjectNames: string[];
};

export type AgentSuggestion = {
  id: string;
  category: string;
  title: string;
  summary: string;
  actionLabel: string;
  href: string;
};

export type PlanRecord = {
  id: string;
  title: string;
  summary: string;
  status: "active" | "queued" | "done";
  statusLabel: string;
  horizon: "today" | "this-week" | "next";
  horizonLabel: string;
  priority: "critical" | "focus" | "steady";
  priorityLabel: string;
  focusLabel: string;
  nextStep: string;
  nextActionLabel: string;
  nextActionHref: string;
  relatedNoteIds: string[];
  relatedSearchTerms: string[];
  agentPrompt: string;
  updatedAt: string;
};

export type NoteRecord = {
  id: string;
  title: string;
  excerpt: string;
  body: string[];
  tags: string[];
  folder: string;
  updatedAt: string;
  readingMinutes: number;
  words: number;
  published: boolean;
  visibility: "private" | "public";
  visibilityLabel: string;
  relatedPlanIds: string[];
  relatedSearchTerms: string[];
  knowledgeStateLabel: string;
  slug?: string;
};

export type WorkbenchSummary = {
  activePlans: number;
  privateNotes: number;
  publishedNotes: number;
};

export type KnowledgeHubSummary = {
  totalNotes: number;
  privateNotes: number;
  publicNotes: number;
  linkedNotes: number;
};

export type KnowledgeFilter = "all" | "private" | "published" | "recent";

export type SearchHit = {
  note: NoteRecord;
  score: number;
  hitLabels: string[];
};

export type PublishSummary = {
  publishedNotes: number;
  privateNotes: number;
  workflowLinkedNotes: number;
};

export type PlanWorkbenchSummary = {
  todayPlans: number;
  activePlans: number;
  queuedPlans: number;
  linkedNotes: number;
};

export type PlanWorkflowLane = {
  key: "today" | "active" | "queued";
  title: string;
  description: string;
  plans: PlanRecord[];
};

export const authorProfile: AuthorProfile = {
  name: "R",
  title: "构建超级个人工作台的人",
  summary: "这里公开我的长期写作、正在搭建的系统，以及我如何把笔记、Agent 与任务计划组织成一个持续运转的个人主系统。",
  intro: "我在把 Inkdesk 打造成一个长期使用的超级个人工作台。它的核心是围绕长期项目运转的个人主系统，而公开输出层负责把已经成熟的判断、文章和项目分享出去。",
  manifesto: "我相信个人系统不该只是存文档，而应该帮助人持续思考、推进项目、组织行动。",
  focusAreas: ["超级个人工作台", "个人知识系统", "Agent 协同", "长期项目"],
  researchStatement:
    "我把公开侧当成一份长期研究索引。这里不追求频繁更新，而是整理那些经过反复工作后仍值得保留的判断、方法和项目痕迹。",
  workingNote: "Inkdesk 是这些工作的底层方法与载体：一个把笔记、Agent 与任务计划编织在一起的私人主系统。",
  contactLinks: [
    { label: "Email", href: "mailto:r@inkdesk.local" },
    { label: "GitHub", href: "https://github.com/inkdesk" },
    { label: "Notes", href: "/articles/super-personal-workbench-reframe" }
  ]
};

export const projects: ProjectLink[] = [
  {
    name: "Inkdesk 主系统",
    href: "#inkdesk-system",
    description: "一个由 Agent、笔记系统和任务计划构成的长期个人主系统。",
    kind: "核心项目"
  },
  {
    name: "公开写作实验",
    href: "#public-writing",
    description: "持续整理对产品、系统设计和个人工作方法的公开写作。",
    kind: "写作"
  },
  {
    name: "个人系统链接集",
    href: "#links",
    description: "放置长期项目、思考入口和未来对外开放的导航节点。",
    kind: "链接"
  }
];

export const publicResearchTopics: PublicResearchTopic[] = [
  {
    slug: "personal-knowledge-systems",
    title: "个人知识系统",
    summary: "我关心知识如何持续积累、回到当前工作，并成为长期项目的判断基础。",
    purpose: "这个主题讨论笔记、结构与长期记忆如何从“存档”变成“持续可调用的工作材料”。",
    featuredArticleSlug: "super-personal-workbench-reframe",
    relatedArticleSlugs: ["public-blog-author-portal"],
    relatedProjectNames: ["Inkdesk 主系统", "个人系统链接集"]
  },
  {
    slug: "agent-assisted-workflows",
    title: "Agent 协同",
    summary: "我在研究 Agent 如何参与整理上下文、压缩判断，并帮助推进真实工作。",
    purpose: "这里关注 Agent 在个人系统中的角色边界：它如何协助人，而不是抢走人的判断与节奏。",
    featuredArticleSlug: "super-personal-workbench-reframe",
    relatedArticleSlugs: ["public-blog-author-portal"],
    relatedProjectNames: ["Inkdesk 主系统"]
  },
  {
    slug: "long-term-projects",
    title: "长期项目",
    summary: "我更关心如何让系统陪伴一个人持续几年地思考、记录和推进，而不是只完成短期任务。",
    purpose: "这个主题聚焦长期项目中的节奏、方法和公开输出方式，以及系统如何让项目保持连续性。",
    featuredArticleSlug: "public-blog-author-portal",
    relatedArticleSlugs: ["super-personal-workbench-reframe"],
    relatedProjectNames: ["公开写作实验", "个人系统链接集"]
  }
];

export const agentSuggestions: AgentSuggestion[] = [
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

export const plans: PlanRecord[] = [
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
    relatedSearchTerms: ["公开输出", "发布分享"],
    agentPrompt: "把主系统入口与公开输出边界压缩成一份可执行检查清单。",
    updatedAt: "2026-04-12 18:30"
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
    relatedSearchTerms: ["Agent", "系统设计"],
    agentPrompt: "从当前笔记和计划里提炼今天最值得推进的一件事。",
    updatedAt: "2026-04-12 17:56"
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
    relatedSearchTerms: ["公开输出", "发布分享"],
    agentPrompt: "判断哪些知识资产已经成熟到可以发布到公开输出。",
    updatedAt: "2026-04-12 17:10"
  }
];

export const notes: NoteRecord[] = [
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
      "Agent 不是为了替代人，而是为了让主系统具备建议、汇总和组织下一步动作的能力。"
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
    relatedSearchTerms: ["Agent", "系统设计", "首页"],
    knowledgeStateLabel: "仅主系统"
  },
  {
    id: "note-003",
    title: "公开输出页作为分享层的结构草案",
    excerpt: "公开输出层应该同时承载已发布文章、作者介绍和长期项目分享，而不是产品官网式 landing page。",
    body: [
      "公开输出层是别人理解作者与已发布内容的入口，而不是进入私有系统的入口。因此它需要克制、清晰，并且完全去掉主人入口提示。",
      "作者介绍、公开文章和项目链接这三个模块可以共同构成一个长期有效的公开输出首页。"
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
    relatedSearchTerms: ["公开输出", "发布分享", "公开文章"],
    knowledgeStateLabel: "已发布",
    slug: "public-blog-author-portal"
  }
];

export const publishedArticles = notes.filter((note) => note.published);

export const workbenchSummary: WorkbenchSummary = {
  activePlans: plans.filter((plan) => plan.status === "active").length,
  privateNotes: notes.filter((note) => !note.published).length,
  publishedNotes: notes.filter((note) => note.published).length
};

export const knowledgeHubSummary: KnowledgeHubSummary = {
  totalNotes: notes.length,
  privateNotes: notes.filter((note) => note.visibility === "private").length,
  publicNotes: notes.filter((note) => note.visibility === "public").length,
  linkedNotes: notes.filter((note) => note.relatedPlanIds.length > 0).length
};

export const publishSummary: PublishSummary = {
  publishedNotes: notes.filter((note) => note.visibility === "public").length,
  privateNotes: notes.filter((note) => note.visibility === "private").length,
  workflowLinkedNotes: notes.filter((note) => note.relatedPlanIds.length > 0).length
};

export const planWorkbenchSummary: PlanWorkbenchSummary = {
  todayPlans: plans.filter((plan) => plan.horizon === "today" && plan.status !== "done").length,
  activePlans: plans.filter((plan) => plan.status === "active").length,
  queuedPlans: plans.filter((plan) => plan.status === "queued").length,
  linkedNotes: new Set(plans.flatMap((plan) => plan.relatedNoteIds)).size
};

function updatedAtValue(updatedAt: string) {
  return Date.parse(updatedAt.replace(" ", "T"));
}

function sortNotesByUpdatedAt(records: NoteRecord[]) {
  return [...records].sort((left, right) => updatedAtValue(right.updatedAt) - updatedAtValue(left.updatedAt));
}

function sortPlansByUpdatedAt(records: PlanRecord[]) {
  return [...records].sort((left, right) => updatedAtValue(right.updatedAt) - updatedAtValue(left.updatedAt));
}

function orderByIds<T extends { id: string }>(records: T[], ids: string[]) {
  const order = new Map(ids.map((id, index) => [id, index]));

  return [...records].sort((left, right) => (order.get(left.id) ?? Number.MAX_SAFE_INTEGER) - (order.get(right.id) ?? Number.MAX_SAFE_INTEGER));
}

export function normalizeKnowledgeFilter(value?: string): KnowledgeFilter {
  switch (value) {
    case "private":
    case "published":
    case "recent":
      return value;
    default:
      return "all";
  }
}

export function filterKnowledgeNotes(filter: KnowledgeFilter = "all") {
  const sorted = sortNotesByUpdatedAt(notes);

  switch (filter) {
    case "private":
      return sorted.filter((note) => note.visibility === "private");
    case "published":
      return sorted.filter((note) => note.visibility === "public");
    case "recent":
      return sorted.slice(0, 2);
    case "all":
    default:
      return sorted;
  }
}

export function getPlanRecordsByIds(ids: string[]) {
  return orderByIds(plans.filter((plan) => ids.includes(plan.id)), ids);
}

export function getNotesByIds(ids: string[]) {
  return orderByIds(notes.filter((note) => ids.includes(note.id)), ids);
}

export function getPlanWorkflowLanes(): PlanWorkflowLane[] {
  return [
    {
      key: "today",
      title: "今天推进",
      description: "先把今天必须收口的事项处理掉，让主系统继续向前。",
      plans: sortPlansByUpdatedAt(plans.filter((plan) => plan.horizon === "today" && plan.status !== "done"))
    },
    {
      key: "active",
      title: "持续推进",
      description: "这些计划还需要连续几轮迭代，不抢第一屏，但不能掉出视野。",
      plans: sortPlansByUpdatedAt(plans.filter((plan) => plan.status === "active" && plan.horizon !== "today"))
    },
    {
      key: "queued",
      title: "等待下一轮",
      description: "方向已经明确，先暂存为下一轮的行动入口。",
      plans: sortPlansByUpdatedAt(plans.filter((plan) => plan.status === "queued"))
    }
  ];
}

export function getRecommendedSearchTerms() {
  return Array.from(new Set(notes.flatMap((note) => note.relatedSearchTerms))).slice(0, 6);
}

export function getRecentKnowledgeNotes() {
  return sortNotesByUpdatedAt(notes).slice(0, 3);
}

export function getOtherPublishedArticles(slug: string) {
  return sortNotesByUpdatedAt(publishedArticles.filter((article) => article.slug !== slug)).slice(0, 2);
}

export function searchKnowledgeNotes(query: string): SearchHit[] {
  const normalized = query.trim().toLowerCase();

  if (!normalized) {
    return [];
  }

  return sortNotesByUpdatedAt(notes)
    .map((note) => {
      const hitLabels: string[] = [];
      let score = 0;

      if (note.title.toLowerCase().includes(normalized)) {
        score += 6;
        hitLabels.push("标题");
      }

      if (note.tags.some((tag) => tag.toLowerCase().includes(normalized))) {
        score += 5;
        hitLabels.push("标签");
      }

      if (note.excerpt.toLowerCase().includes(normalized)) {
        score += 4;
        hitLabels.push("摘要");
      }

      if (note.folder.toLowerCase().includes(normalized)) {
        score += 3;
        hitLabels.push("文件夹");
      }

      if (note.body.some((paragraph) => paragraph.toLowerCase().includes(normalized))) {
        score += 2;
        hitLabels.push("正文");
      }

      return {
        note,
        score,
        hitLabels
      };
    })
    .filter((result) => result.score > 0)
    .sort((left, right) => right.score - left.score || updatedAtValue(right.note.updatedAt) - updatedAtValue(left.note.updatedAt));
}

export function getNote(id: string) {
  return notes.find((note) => note.id === id) ?? notes[0];
}

export function getArticle(slug: string) {
  return publishedArticles.find((article) => article.slug === slug) ?? publishedArticles[0];
}
