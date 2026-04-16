import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import { fetchInkdeskJson, hasApiBaseUrl, InkdeskApiError } from "@/lib/server-api";
import type { ProjectLink, PublicArticleDetail, PublicArticleSummary, PublicHomeData, PublicResearchTopic, PublicResearchTopicDetail } from "@/lib/types";

type BackendPublicArticleSummary = {
  id: string;
  title: string;
  excerpt: string | null;
  slug: string;
  updatedAt: string;
  tags: string[];
};

type BackendPublicArticleDetail = BackendPublicArticleSummary & {
  markdownContent: string;
};

function countWords(value: string) {
  return value
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function estimateReadingMinutes(value: string) {
  return Math.max(1, Math.ceil(countWords(value) / 220));
}

function splitMarkdownParagraphs(markdownContent: string) {
  return markdownContent
    .split(/\r?\n\s*\r?\n/)
    .map((paragraph) => paragraph.replace(/\r?\n/g, " ").trim())
    .filter(Boolean);
}

function adaptPublicArticleSummary(record: BackendPublicArticleSummary): PublicArticleSummary {
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.id);

  return {
    id: record.id,
    slug: record.slug,
    title: record.title,
    excerpt: record.excerpt ?? supplement?.excerpt ?? "",
    folder: supplement?.folder ?? "知识资产",
    updatedAt: supplement?.updatedAt ?? record.updatedAt,
    readingMinutes: supplement?.readingMinutes ?? estimateReadingMinutes(record.excerpt ?? record.title),
    tags: record.tags.length > 0 ? record.tags : supplement?.tags ?? [],
    sourceNoteId: record.id
  };
}

function adaptPublicArticleDetail(record: BackendPublicArticleDetail): PublicArticleDetail {
  const summary = adaptPublicArticleSummary(record);
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.id);
  const body = splitMarkdownParagraphs(record.markdownContent);
  const relatedNoteIds = supplement?.relatedPlanIds.flatMap((planId) => mockInkdeskDataSource.getPlanById(planId)?.relatedNoteIds ?? []) ?? [];

  return {
    ...summary,
    body,
    provenance: "这篇文章来自 Inkdesk 主系统中的长期知识资产，经整理后发布到公开输出层，用于分享成熟判断与项目进展。",
    relatedNoteIds: Array.from(new Set(relatedNoteIds.filter((noteId) => noteId !== record.id)))
  };
}

async function getBackendPublicArticles() {
  const records = await fetchInkdeskJson<BackendPublicArticleSummary[]>("/public/articles");
  return records.map(adaptPublicArticleSummary);
}

function fallbackPublicHomeData() {
  return mockInkdeskDataSource.getPublicHomeData();
}

function resolveResearchTopic(
  topic: PublicResearchTopic,
  articles: PublicArticleSummary[],
  projects: ProjectLink[]
): PublicResearchTopicDetail {
  const articleBySlug = new Map(articles.map((article) => [article.slug, article]));
  const relatedArticles = topic.relatedArticleSlugs
    .map((slug) => articleBySlug.get(slug))
    .filter((article): article is PublicArticleSummary => Boolean(article));
  const featuredArticle = articleBySlug.get(topic.featuredArticleSlug) ?? relatedArticles[0];

  return {
    ...topic,
    featuredArticle,
    relatedArticles: relatedArticles.filter((article) => article.slug !== featuredArticle?.slug),
    relatedProjects: topic.relatedProjectNames
      .map((name) => projects.find((project) => project.name === name))
      .filter((project): project is ProjectLink => Boolean(project))
  };
}

function shouldFallbackToMockPublicData(error: unknown) {
  return !(error instanceof InkdeskApiError && error.status === 404);
}

export async function getPublicHomeData(): Promise<PublicHomeData> {
  if (!hasApiBaseUrl()) {
    return fallbackPublicHomeData();
  }

  try {
    const base = fallbackPublicHomeData();
    const articles = await getBackendPublicArticles();

    return {
      authorProfile: base.authorProfile,
      projects: base.projects,
      articles,
      researchTopics: base.researchTopics,
      featuredArticle: articles[0],
      publicStats: [
        { label: "公开文章", value: `${articles.length}`, detail: "已稳定发布出去的文章资产" },
        { label: "长期项目", value: `${base.projects.length}`, detail: "持续对外展示的项目或链接入口" },
        { label: "主系统主题", value: `${base.authorProfile.focusAreas.length}`, detail: "作者持续推进的长期主题" }
      ]
    };
  } catch (error) {
    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return fallbackPublicHomeData();
  }
}

export async function getPublicArticleBySlug(slug: string) {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource.getPublicArticleBySlug(slug);
  }

  try {
    const record = await fetchInkdeskJson<BackendPublicArticleDetail>(`/public/articles/${slug}`);
    return adaptPublicArticleDetail(record);
  } catch (error) {
    if (error instanceof InkdeskApiError && error.status === 404) {
      return undefined;
    }

    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return mockInkdeskDataSource.getPublicArticleBySlug(slug);
  }
}

export async function getOtherPublicArticleSummaries(slug: string) {
  if (!hasApiBaseUrl()) {
    return mockInkdeskDataSource
      .getPublicHomeData()
      .articles.filter((article) => article.slug !== slug)
      .slice(0, 2);
  }

  try {
    const articles = await getBackendPublicArticles();
    return articles.filter((article) => article.slug !== slug).slice(0, 2);
  } catch (error) {
    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return fallbackPublicHomeData()
      .articles.filter((article) => article.slug !== slug)
      .slice(0, 2);
  }
}

export async function getPublicArticleParams() {
  if (!hasApiBaseUrl()) {
    return fallbackPublicHomeData().articles.map((article) => ({
      slug: article.slug
    }));
  }

  try {
    const articles = await getBackendPublicArticles();

    return articles.map((article) => ({
      slug: article.slug
    }));
  } catch (error) {
    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return fallbackPublicHomeData().articles.map((article) => ({
      slug: article.slug
    }));
  }
}

export async function getPublicResearchTopics() {
  const home = await getPublicHomeData();
  return home.researchTopics;
}

export async function getPublicResearchTopicBySlug(slug: string) {
  const home = await getPublicHomeData();
  const topic = home.researchTopics.find((entry) => entry.slug === slug);

  if (!topic) {
    return undefined;
  }

  return resolveResearchTopic(topic, home.articles, home.projects);
}

export async function getPublicResearchParams() {
  const topics = await getPublicResearchTopics();

  return topics.map((topic) => ({
    slug: topic.slug
  }));
}

export async function getPublicResearchTopicsForArticleSlug(slug: string) {
  const home = await getPublicHomeData();

  return home.researchTopics
    .filter((topic) => topic.featuredArticleSlug === slug || topic.relatedArticleSlugs.includes(slug))
    .map((topic) => resolveResearchTopic(topic, home.articles, home.projects));
}
