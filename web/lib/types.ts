export type NoteStatus = "blank" | "loading" | "draft" | "saving" | "error" | "published";

export type AsyncState = "idle" | "loading" | "success" | "error";

export type FormState = "idle" | "pending" | "success" | "error";

export type EmptyStateReason =
  | "no-public-articles"
  | "no-knowledge"
  | "no-plans"
  | "no-tags"
  | "no-search-results"
  | "not-found";

export type Visibility = "private" | "public";

export type PublishState = "draft" | "published";

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

export type PublicStat = {
  label: string;
  value: string;
  detail: string;
};

export type AgentSuggestion = {
  id: string;
  category: string;
  title: string;
  summary: string;
  actionLabel: string;
  href: string;
};

export type QuickAction = {
  id: string;
  label: string;
  summary: string;
  href: string;
  icon: string;
};

export type PublicArticleSummary = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  folder: string;
  updatedAt: string;
  readingMinutes: number;
  tags: string[];
  sourceNoteId: string;
};

export type PublicArticleDetail = PublicArticleSummary & {
  body: string[];
  provenance: string;
  relatedNoteIds: string[];
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

export type PublicResearchTopicDetail = PublicResearchTopic & {
  featuredArticle?: PublicArticleSummary;
  relatedArticles: PublicArticleSummary[];
  relatedProjects: ProjectLink[];
};

export type KnowledgeNoteSummary = {
  id: string;
  title: string;
  excerpt: string;
  tags: string[];
  folder: string;
  updatedAt: string;
  readingMinutes: number;
  words: number;
  published: boolean;
  visibility: Visibility;
  visibilityLabel: string;
  relatedPlanIds: string[];
  relatedTagIds: string[];
  relatedSearchTerms: string[];
  knowledgeStateLabel: string;
  slug?: string;
};

export type KnowledgeNoteDetail = KnowledgeNoteSummary & {
  parentId?: string | null;
  body: string[];
};

export type PlanStatus = "active" | "queued" | "done";

export type PlanHorizon = "today" | "this-week" | "next";

export type PlanPriority = "critical" | "focus" | "steady";

export type PlanSummary = {
  id: string;
  title: string;
  summary: string;
  status: PlanStatus;
  statusLabel: string;
  horizon: PlanHorizon;
  horizonLabel: string;
  priority: PlanPriority;
  priorityLabel: string;
  focusLabel: string;
  nextStep: string;
  nextActionLabel: string;
  nextActionHref: string;
  relatedNoteIds: string[];
  relatedTagIds: string[];
  relatedSearchTerms: string[];
  agentPrompt: string;
  updatedAt: string;
};

export type PlanDetail = PlanSummary & {
  milestones: string[];
};

export type SearchQuery = {
  q: string;
  visibility?: Visibility | "all";
  tag?: string;
  folder?: string;
};

export type SearchResult = {
  note: KnowledgeNoteSummary;
  score: number;
  hitLabels: string[];
  matchedTerms: string[];
};

export type PublishEntry = {
  noteId: string;
  title: string;
  excerpt: string;
  slug?: string;
  updatedAt: string;
  state: PublishState;
  stateLabel: string;
  visibilityLabel: string;
  publicPath?: string;
  relatedPlanIds: string[];
};

export type TagRecord = {
  id: string;
  label: string;
  tone: string;
  description: string;
  noteIds: string[];
  planIds: string[];
  articleSlugs: string[];
  usageCount: number;
};

export type SettingsRecord = {
  profile: {
    displayName: string;
    publicTitle: string;
    summary: string;
    publicLocation: string;
  };
  workbench: {
    defaultPage: string;
    compactMode: boolean;
    showContextRibbon: boolean;
  };
  editor: {
    defaultView: "edit" | "preview" | "read";
    autoSave: boolean;
    publishReminder: boolean;
  };
  publish: {
    defaultAudience: "public" | "private";
    showProvenance: boolean;
    highlightRecentUpdates: boolean;
  };
  security: {
    ownerEmail: string;
    sessionMode: string;
    sessionDurationLabel: string;
  };
};

export type WorkbenchSnapshot = {
  summary: {
    activePlans: number;
    privateNotes: number;
    publishedNotes: number;
    linkedNotes: number;
  };
  focusPlan: PlanDetail;
  focusNote: KnowledgeNoteSummary;
  suggestions: AgentSuggestion[];
  quickActions: QuickAction[];
  recentKnowledge: KnowledgeNoteSummary[];
  publishQueue: PublishEntry[];
};

export type KnowledgeHubData = {
  summary: {
    totalNotes: number;
    privateNotes: number;
    publicNotes: number;
    linkedNotes: number;
  };
  notes: KnowledgeNoteSummary[];
  filters: Array<{
    value: string;
    label: string;
  }>;
  tagHighlights: TagRecord[];
  recentActivity: string[];
};

export type PlanWorkbenchData = {
  summary: {
    todayPlans: number;
    activePlans: number;
    queuedPlans: number;
    linkedNotes: number;
  };
  lanes: Array<{
    key: "today" | "active" | "queued";
    title: string;
    description: string;
    plans: PlanDetail[];
  }>;
};

export type PublishDashboard = {
  summary: {
    publishedNotes: number;
    privateNotes: number;
    workflowLinkedNotes: number;
  };
  published: PublishEntry[];
  drafts: PublishEntry[];
};

export type PublicHomeData = {
  authorProfile: AuthorProfile;
  featuredArticle?: PublicArticleSummary;
  articles: PublicArticleSummary[];
  projects: ProjectLink[];
  publicStats: PublicStat[];
  researchTopics: PublicResearchTopic[];
};

export type InkdeskDataSource = {
  getAuthSession(): {
    isAuthenticated: boolean;
    ownerLabel: string;
    entryPath: string;
  };
  getPublicHomeData(): PublicHomeData;
  getPublicArticleBySlug(slug: string): PublicArticleDetail | undefined;
  getWorkbenchSnapshot(): WorkbenchSnapshot;
  getKnowledgeHubData(filter?: string): KnowledgeHubData;
  getKnowledgeNoteById(id: string): KnowledgeNoteDetail | undefined;
  getPlanWorkbenchData(): PlanWorkbenchData;
  getPlanById(id: string): PlanDetail | undefined;
  searchKnowledge(query: SearchQuery): SearchResult[];
  getPublishDashboard(): PublishDashboard;
  getTagRecords(): TagRecord[];
  getSettingsRecord(): SettingsRecord;
};
