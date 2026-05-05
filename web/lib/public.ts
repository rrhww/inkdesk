import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import { fetchInkdeskJson, hasApiBaseUrl, InkdeskApiError } from "@/lib/server-api";
import type {
  PublicArticleDetail,
  PublicArticleRelations,
  PublicArticleSummary,
  PublicHomeData,
  PublicKnowledgeBucket,
  PublicKnowledgeBucketDetail,
  PublicProject,
  PublicProjectDetail,
  PublicUpdateItem
} from "@/lib/types";

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

function updatedAtValue(updatedAt: string) {
  return Date.parse(updatedAt.replace(" ", "T"));
}

function sortByUpdatedAt<T extends { updatedAt: string }>(records: T[]) {
  return [...records].sort((left, right) => updatedAtValue(right.updatedAt) - updatedAtValue(left.updatedAt));
}

function mergePublicArticles(preferredArticles: PublicArticleSummary[], fallbackArticles: PublicArticleSummary[]) {
  const articleBySlug = new Map(fallbackArticles.map((article) => [article.slug, article]));

  for (const article of preferredArticles) {
    articleBySlug.set(article.slug, article);
  }

  return sortByUpdatedAt(Array.from(articleBySlug.values()));
}

function adaptPublicArticleSummary(record: BackendPublicArticleSummary): PublicArticleSummary {
  const supplement = mockInkdeskDataSource.getKnowledgeNoteById(record.id);

  return {
    id: record.id,
    slug: record.slug,
    title: record.title,
    excerpt: record.excerpt ?? supplement?.excerpt ?? "",
    folder: supplement?.folder ?? "公开笔记",
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

function resolveKnowledgeBucket(
  bucket: PublicKnowledgeBucket,
  articles: PublicArticleSummary[],
  projects: PublicProject[]
): PublicKnowledgeBucketDetail {
  const articleBySlug = new Map(articles.map((article) => [article.slug, article]));

  return {
    ...bucket,
    featuredArticle: articleBySlug.get(bucket.featuredArticleSlug),
    relatedArticles: bucket.relatedArticleSlugs
      .map((slug) => articleBySlug.get(slug))
      .filter((article): article is PublicArticleSummary => Boolean(article)),
    relatedProjects: bucket.relatedProjectSlugs
      .map((slug) => projects.find((project) => project.slug === slug))
      .filter((project): project is PublicProject => Boolean(project))
  };
}

function resolveProject(
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

function createMixedUpdates(articles: PublicArticleSummary[], projects: PublicProject[]): PublicUpdateItem[] {
  const articleUpdates = articles.slice(0, 4).map<PublicUpdateItem>((article, index) => ({
    id: `article-${article.slug}`,
    type: "article",
    title: article.title,
    summary: article.excerpt,
    href: `/articles/${article.slug}`,
    updatedAt: article.updatedAt,
    label: index === 0 ? "新文章" : "分类代表"
  }));
  const projectUpdates = sortByUpdatedAt(projects)
    .slice(0, 2)
    .map<PublicUpdateItem>((project) => ({
      id: `project-${project.slug}`,
      type: "project",
      title: project.title,
      summary: project.summary,
      href: `/projects/${project.slug}`,
      updatedAt: project.updatedAt,
      label: "项目更新"
    }));

  return sortByUpdatedAt([...articleUpdates, ...projectUpdates]).slice(0, 6);
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
    const articles = mergePublicArticles(await getBackendPublicArticles(), base.articles);

    return {
      authorProfile: base.authorProfile,
      articles,
      knowledgeBuckets: base.knowledgeBuckets,
      featuredProjects: base.featuredProjects,
      recentUpdates: createMixedUpdates(articles, base.featuredProjects),
      contactLinks: base.contactLinks
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
      return mockInkdeskDataSource.getPublicArticleBySlug(slug);
    }

    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return mockInkdeskDataSource.getPublicArticleBySlug(slug);
  }
}

export async function getOtherPublicArticleSummaries(slug: string) {
  const base = fallbackPublicHomeData();

  if (!hasApiBaseUrl()) {
    return base.articles.filter((article) => article.slug !== slug).slice(0, 2);
  }

  try {
    const articles = mergePublicArticles(await getBackendPublicArticles(), base.articles);
    return articles.filter((article) => article.slug !== slug).slice(0, 2);
  } catch (error) {
    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return base.articles.filter((article) => article.slug !== slug).slice(0, 2);
  }
}

export async function getPublicArticleParams() {
  const base = fallbackPublicHomeData();

  if (!hasApiBaseUrl()) {
    return base.articles.map((article) => ({
      slug: article.slug
    }));
  }

  try {
    const articles = mergePublicArticles(await getBackendPublicArticles(), base.articles);

    return articles.map((article) => ({
      slug: article.slug
    }));
  } catch (error) {
    if (!shouldFallbackToMockPublicData(error)) {
      throw error;
    }

    return base.articles.map((article) => ({
      slug: article.slug
    }));
  }
}

export async function getPublicKnowledgeBuckets() {
  return (await getPublicHomeData()).knowledgeBuckets;
}

export async function getPublicKnowledgeBucketBySlug(slug: string) {
  const home = await getPublicHomeData();
  const bucket = home.knowledgeBuckets.find((entry) => entry.slug === slug);

  if (!bucket) {
    return undefined;
  }

  return resolveKnowledgeBucket(bucket, home.articles, home.featuredProjects);
}

export async function getPublicKnowledgeBucketParams() {
  return (await getPublicKnowledgeBuckets()).map((bucket) => ({
    slug: bucket.slug
  }));
}

export async function getPublicProjects() {
  return (await getPublicHomeData()).featuredProjects;
}

export async function getPublicProjectBySlug(slug: string) {
  const home = await getPublicHomeData();
  const project = home.featuredProjects.find((entry) => entry.slug === slug);

  if (!project) {
    return undefined;
  }

  return resolveProject(project, home.articles, home.knowledgeBuckets);
}

export async function getPublicProjectParams() {
  return (await getPublicProjects()).map((project) => ({
    slug: project.slug
  }));
}

export async function getPublicRelationsForArticleSlug(slug: string): Promise<PublicArticleRelations> {
  const home = await getPublicHomeData();

  return {
    relatedBuckets: home.knowledgeBuckets
      .filter((bucket) => bucket.featuredArticleSlug === slug || bucket.relatedArticleSlugs.includes(slug))
      .map((bucket) => resolveKnowledgeBucket(bucket, home.articles, home.featuredProjects)),
    relatedProjects: home.featuredProjects
      .filter((project) => project.relatedArticleSlugs.includes(slug))
      .map((project) => resolveProject(project, home.articles, home.knowledgeBuckets))
  };
}
