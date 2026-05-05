import {
  agentSuggestionsFixture,
  authorProfileFixture,
  notesFixture,
  plansFixture,
  publicArticleFixtures,
  publicKnowledgeBucketsFixture,
  publicProjectsFixture,
  publicUpdatesFixture,
  quickActionsFixture,
  settingsFixture,
  tagsFixture
} from "@/lib/mock/fixtures";
import type {
  InkdeskDataSource,
  KnowledgeHubData,
  KnowledgeNoteDetail,
  KnowledgeNoteSummary,
  PlanWorkbenchData,
  PublicArticleDetail,
  PublicArticleSummary,
  PublicHomeData,
  PublicKnowledgeBucket,
  PublicKnowledgeBucketDetail,
  PublicProject,
  PublicProjectDetail,
  PublishDashboard,
  PublishEntry,
  SearchQuery,
  SearchResult,
  TagRecord,
  WorkbenchSnapshot
} from "@/lib/types";

function updatedAtValue(updatedAt: string) {
  return Date.parse(updatedAt.replace(" ", "T"));
}

function sortByUpdatedAt<T extends { updatedAt: string }>(records: T[]) {
  return [...records].sort((left, right) => updatedAtValue(right.updatedAt) - updatedAtValue(left.updatedAt));
}

function toNoteSummary(note: KnowledgeNoteDetail): KnowledgeNoteSummary {
  return {
    id: note.id,
    title: note.title,
    excerpt: note.excerpt,
    tags: note.tags,
    folder: note.folder,
    updatedAt: note.updatedAt,
    readingMinutes: note.readingMinutes,
    words: note.words,
    published: note.published,
    visibility: note.visibility,
    visibilityLabel: note.visibilityLabel,
    relatedPlanIds: note.relatedPlanIds,
    relatedTagIds: note.relatedTagIds,
    relatedSearchTerms: note.relatedSearchTerms,
    knowledgeStateLabel: note.knowledgeStateLabel,
    slug: note.slug
  };
}

function toArticleSummary(article: PublicArticleDetail): PublicArticleSummary {
  return {
    id: article.id,
    slug: article.slug,
    title: article.title,
    excerpt: article.excerpt,
    folder: article.folder,
    updatedAt: article.updatedAt,
    readingMinutes: article.readingMinutes,
    tags: article.tags,
    sourceNoteId: article.sourceNoteId
  };
}

function toPublishEntry(note: KnowledgeNoteDetail): PublishEntry {
  return {
    noteId: note.id,
    title: note.title,
    excerpt: note.excerpt,
    slug: note.slug,
    updatedAt: note.updatedAt,
    state: note.published ? "published" : "draft",
    stateLabel: note.published ? "已发布" : "继续整理后发布",
    visibilityLabel: note.visibilityLabel,
    publicPath: note.slug ? `/articles/${note.slug}` : undefined,
    relatedPlanIds: note.relatedPlanIds
  };
}

function getNoteByIdLocal(id: string) {
  return notesFixture.find((note) => note.id === id);
}

function getPlanByIdLocal(id: string) {
  return plansFixture.find((plan) => plan.id === id);
}

function getTagByIdLocal(id: string) {
  return tagsFixture.find((tag) => tag.id === id);
}

function getPublishedArticlesLocal() {
  return sortByUpdatedAt(publicArticleFixtures);
}

function getPublicArticleSummariesLocal() {
  return getPublishedArticlesLocal().map((article) => toArticleSummary(article));
}

function resolveKnowledgeBucketLocal(
  bucket: PublicKnowledgeBucket,
  articles: PublicArticleSummary[],
  projects: PublicProject[]
): PublicKnowledgeBucketDetail {
  const articleBySlug = new Map(articles.map((article) => [article.slug, article]));
  const featuredArticle = articleBySlug.get(bucket.featuredArticleSlug);
  const relatedArticles = bucket.relatedArticleSlugs
    .map((slug) => articleBySlug.get(slug))
    .filter((article): article is PublicArticleSummary => Boolean(article));

  return {
    ...bucket,
    featuredArticle,
    relatedArticles,
    relatedProjects: bucket.relatedProjectSlugs
      .map((slug) => projects.find((project) => project.slug === slug))
      .filter((project): project is PublicProject => Boolean(project))
  };
}

function resolveProjectLocal(
  project: PublicProject,
  articles: PublicArticleSummary[],
  buckets: PublicKnowledgeBucket[]
): PublicProjectDetail {
  return {
    ...project,
    relatedArticles: project.relatedArticleSlugs
      .map((slug) => articles.find((article) => article.slug === slug))
      .filter((article): article is PublicArticleSummary => Boolean(article)),
    relatedBuckets: project.relatedBucketSlugs
      .map((slug) => buckets.find((bucket) => bucket.slug === slug))
      .filter((bucket): bucket is PublicKnowledgeBucket => Boolean(bucket))
  };
}

function normalizeKnowledgeFilter(value?: string) {
  switch (value) {
    case "private":
    case "published":
    case "recent":
      return value;
    default:
      return "all";
  }
}

function filterKnowledgeNotesLocal(filter?: string) {
  const normalized = normalizeKnowledgeFilter(filter);
  const sorted = sortByUpdatedAt(notesFixture).map((note) => toNoteSummary(note));

  switch (normalized) {
    case "private":
      return sorted.filter((note) => note.visibility === "private");
    case "published":
      return sorted.filter((note) => note.visibility === "public");
    case "recent":
      return sorted.slice(0, 2);
    default:
      return sorted;
  }
}

function searchKnowledgeLocal(query: SearchQuery): SearchResult[] {
  const normalized = query.q.trim().toLowerCase();

  if (!normalized) {
    return [];
  }

  return sortByUpdatedAt(notesFixture)
    .map((note) => {
      const hitLabels: string[] = [];
      const matchedTerms: string[] = [];
      let score = 0;

      if (query.visibility && query.visibility !== "all" && note.visibility !== query.visibility) {
        return {
          note,
          score: 0,
          hitLabels,
          matchedTerms
        };
      }

      if (query.tag && !note.tags.includes(query.tag)) {
        return {
          note,
          score: 0,
          hitLabels,
          matchedTerms
        };
      }

      if (query.folder && note.folder !== query.folder) {
        return {
          note,
          score: 0,
          hitLabels,
          matchedTerms
        };
      }

      if (note.title.toLowerCase().includes(normalized)) {
        score += 6;
        hitLabels.push("标题");
        matchedTerms.push(note.title);
      }

      if (note.tags.some((tag) => tag.toLowerCase().includes(normalized))) {
        score += 5;
        hitLabels.push("标签");
        matchedTerms.push(...note.tags.filter((tag) => tag.toLowerCase().includes(normalized)));
      }

      if (note.excerpt.toLowerCase().includes(normalized)) {
        score += 4;
        hitLabels.push("摘要");
        matchedTerms.push(note.excerpt);
      }

      if (note.folder.toLowerCase().includes(normalized)) {
        score += 3;
        hitLabels.push("文件夹");
        matchedTerms.push(note.folder);
      }

      if (note.body.some((paragraph) => paragraph.toLowerCase().includes(normalized))) {
        score += 2;
        hitLabels.push("正文");
        matchedTerms.push(note.body.find((paragraph) => paragraph.toLowerCase().includes(normalized)) ?? "");
      }

      return {
        note,
        score,
        hitLabels,
        matchedTerms
      };
    })
    .filter((result) => result.score > 0)
    .sort((left, right) => right.score - left.score || updatedAtValue(right.note.updatedAt) - updatedAtValue(left.note.updatedAt))
    .map((result) => ({
      note: toNoteSummary(result.note),
      score: result.score,
      hitLabels: Array.from(new Set(result.hitLabels)),
      matchedTerms: result.matchedTerms.filter(Boolean)
    }));
}

function getKnowledgeHubDataLocal(filter?: string): KnowledgeHubData {
  const notes = filterKnowledgeNotesLocal(filter);

  return {
    summary: {
      totalNotes: notesFixture.length,
      privateNotes: notesFixture.filter((note) => note.visibility === "private").length,
      publicNotes: notesFixture.filter((note) => note.visibility === "public").length,
      linkedNotes: notesFixture.filter((note) => note.relatedPlanIds.length > 0).length
    },
    notes,
    filters: [
      { value: "all", label: "全部" },
      { value: "private", label: "仅主系统" },
      { value: "published", label: "已发布" },
      { value: "recent", label: "最近更新" }
    ],
    tagHighlights: tagsFixture.slice(0, 3),
    recentActivity: sortByUpdatedAt(notesFixture).map((note) => `${note.updatedAt} · ${note.title}`).slice(0, 3)
  };
}

function getPlanWorkbenchDataLocal(): PlanWorkbenchData {
  return {
    summary: {
      todayPlans: plansFixture.filter((plan) => plan.horizon === "today" && plan.status !== "done").length,
      activePlans: plansFixture.filter((plan) => plan.status === "active").length,
      queuedPlans: plansFixture.filter((plan) => plan.status === "queued").length,
      linkedNotes: new Set(plansFixture.flatMap((plan) => plan.relatedNoteIds)).size
    },
    lanes: [
      {
        key: "today",
        title: "今天推进",
        description: "先把今天必须收口的事项处理掉，让主系统继续向前。",
        plans: sortByUpdatedAt(plansFixture.filter((plan) => plan.horizon === "today" && plan.status !== "done"))
      },
      {
        key: "active",
        title: "持续推进",
        description: "这些计划还需要连续几轮迭代，不抢第一屏，但不能掉出视野。",
        plans: sortByUpdatedAt(plansFixture.filter((plan) => plan.status === "active" && plan.horizon !== "today"))
      },
      {
        key: "queued",
        title: "等待下一轮",
        description: "方向已经明确，先暂存为下一轮的行动入口。",
        plans: sortByUpdatedAt(plansFixture.filter((plan) => plan.status === "queued"))
      }
    ]
  };
}

function getWorkbenchSnapshotLocal(): WorkbenchSnapshot {
  const focusPlan = plansFixture[0];
  const focusNote = toNoteSummary(notesFixture.find((note) => !note.published) ?? notesFixture[0]);
  const publishQueue = sortByUpdatedAt(notesFixture.filter((note) => !note.published)).map((note) => toPublishEntry(note));

  return {
    summary: {
      activePlans: plansFixture.filter((plan) => plan.status === "active").length,
      privateNotes: notesFixture.filter((note) => !note.published).length,
      publishedNotes: notesFixture.filter((note) => note.published).length,
      linkedNotes: notesFixture.filter((note) => note.relatedPlanIds.length > 0).length
    },
    focusPlan,
    focusNote,
    suggestions: agentSuggestionsFixture,
    quickActions: quickActionsFixture,
    recentKnowledge: sortByUpdatedAt(notesFixture).map((note) => toNoteSummary(note)).slice(0, 3),
    publishQueue
  };
}

function getPublishDashboardLocal(): PublishDashboard {
  const entries = sortByUpdatedAt(notesFixture).map((note) => toPublishEntry(note));

  return {
    summary: {
      publishedNotes: notesFixture.filter((note) => note.visibility === "public").length,
      privateNotes: notesFixture.filter((note) => note.visibility === "private").length,
      workflowLinkedNotes: notesFixture.filter((note) => note.relatedPlanIds.length > 0).length
    },
    published: entries.filter((entry) => entry.state === "published"),
    drafts: entries.filter((entry) => entry.state === "draft")
  };
}

function getPublicHomeDataLocal(): PublicHomeData {
  const articles = getPublicArticleSummariesLocal();

  return {
    authorProfile: authorProfileFixture,
    articles,
    knowledgeBuckets: publicKnowledgeBucketsFixture,
    featuredProjects: sortByUpdatedAt(publicProjectsFixture),
    recentUpdates: sortByUpdatedAt(publicUpdatesFixture).slice(0, 6),
    contactLinks: authorProfileFixture.contactLinks ?? []
  };
}

export const mockInkdeskDataSource: InkdeskDataSource = {
  getAuthSession() {
    return {
      isAuthenticated: false,
      ownerLabel: "主人主系统",
      entryPath: "/login"
    };
  },
  getPublicHomeData() {
    return getPublicHomeDataLocal();
  },
  getPublicArticleBySlug(slug: string) {
    return getPublishedArticlesLocal().find((article) => article.slug === slug);
  },
  getWorkbenchSnapshot() {
    return getWorkbenchSnapshotLocal();
  },
  getKnowledgeHubData(filter?: string) {
    return getKnowledgeHubDataLocal(filter);
  },
  getKnowledgeNoteById(id: string) {
    return getNoteByIdLocal(id);
  },
  getPlanWorkbenchData() {
    return getPlanWorkbenchDataLocal();
  },
  getPlanById(id: string) {
    return getPlanByIdLocal(id);
  },
  searchKnowledge(query: SearchQuery) {
    return searchKnowledgeLocal(query);
  },
  getPublishDashboard() {
    return getPublishDashboardLocal();
  },
  getTagRecords() {
    return tagsFixture;
  },
  getSettingsRecord() {
    return settingsFixture;
  }
};

export function getOtherPublicArticles(slug: string) {
  return getPublishedArticlesLocal().filter((article) => article.slug !== slug).slice(0, 2);
}

export function getPublishedArticles() {
  return getPublishedArticlesLocal();
}

export function getPublicKnowledgeBucketDetail(slug: string) {
  const home = getPublicHomeDataLocal();
  const bucket = home.knowledgeBuckets.find((entry) => entry.slug === slug);

  if (!bucket) {
    return undefined;
  }

  return resolveKnowledgeBucketLocal(bucket, home.articles, home.featuredProjects);
}

export function getPublicProjectDetail(slug: string) {
  const home = getPublicHomeDataLocal();
  const project = home.featuredProjects.find((entry) => entry.slug === slug);

  if (!project) {
    return undefined;
  }

  return resolveProjectLocal(project, home.articles, home.knowledgeBuckets);
}

export function getPublicArticleRelations(slug: string) {
  const home = getPublicHomeDataLocal();
  const relatedBuckets = home.knowledgeBuckets
    .filter((bucket) => bucket.featuredArticleSlug === slug || bucket.relatedArticleSlugs.includes(slug))
    .map((bucket) => resolveKnowledgeBucketLocal(bucket, home.articles, home.featuredProjects));
  const relatedProjects = home.featuredProjects
    .filter((project) => project.relatedArticleSlugs.includes(slug))
    .map((project) => resolveProjectLocal(project, home.articles, home.knowledgeBuckets));

  return {
    relatedBuckets,
    relatedProjects
  };
}

export function getKnowledgeSummariesByIds(ids: string[]) {
  return ids
    .map((id) => getNoteByIdLocal(id))
    .filter((note): note is KnowledgeNoteDetail => Boolean(note))
    .map((note) => toNoteSummary(note));
}

export function getTagRecordsByIds(ids: string[]): TagRecord[] {
  return ids.map((id) => getTagByIdLocal(id)).filter((tag): tag is TagRecord => Boolean(tag));
}

export function getRecommendedSearchTerms() {
  return Array.from(new Set(notesFixture.flatMap((note) => note.relatedSearchTerms))).slice(0, 8);
}

export function getRecentKnowledgeSummaries() {
  return sortByUpdatedAt(notesFixture).map((note) => toNoteSummary(note)).slice(0, 3);
}

export function getKnowledgeFolders() {
  return Array.from(new Set(notesFixture.map((note) => note.folder)));
}

export function getKnowledgeTags() {
  return tagsFixture.map((tag) => tag.label);
}

export function filterKnowledgeNotes(filter?: string) {
  return filterKnowledgeNotesLocal(filter);
}
