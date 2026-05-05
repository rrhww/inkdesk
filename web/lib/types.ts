export type ResearchSourceKind = "TEXT" | "WEB" | "PDF" | "LEGACY_NOTE";

export type ResearchSourceStatus = "RAW" | "INGEST_PENDING" | "WIKI_LINKED" | "IGNORED";

export type ResearchReviewKind = "TOPIC_CREATE" | "TOPIC_PATCH";

export type ResearchProposalKind = "TOPIC_CREATE" | "TOPIC_PATCH";

export type ResearchThreadRole = "USER" | "ASSISTANT" | "SYSTEM";

export type ResearchAskMode = "vault" | "vault_plus_web";

export type ResearchTopicSummary = {
  id: string;
  title: string;
  summary: string;
  sourceCount: number;
  openQuestionCount: number;
  vaultPath?: string | null;
  updatedAt: string;
};

export type ResearchSourceRecord = {
  id: string;
  kind: ResearchSourceKind;
  status: ResearchSourceStatus;
  title: string;
  locator?: string | null;
  excerpt: string;
  legacyNoteId?: string | null;
  vaultPath?: string | null;
  contentHash?: string | null;
  updatedAt: string;
};

export type ResearchReviewItem = {
  id: string;
  kind: ResearchReviewKind;
  proposalKind?: ResearchProposalKind | null;
  title: string;
  summary: string;
  sourceId?: string | null;
  sourceTitle?: string | null;
  targetTopicId?: string | null;
  targetTopicTitle?: string | null;
  proposedTopicTitle?: string | null;
  proposedUnderstanding?: string | null;
  proposedOpenQuestions?: string | null;
  proposedClaim?: string | null;
  proposedVaultPath?: string | null;
  sourceVaultPath?: string | null;
  proposalPayload?: ResearchProposalPayload | null;
  createdAt: string;
};

export type ResearchProposalPayload = {
  topicDecision: ResearchProposalTopicDecision;
  summaryChanges: string[];
  claims: ResearchProposalClaim[];
  conflicts: string[];
  openQuestions: string[];
  explanation: string;
  evidence: ResearchProposalEvidence[];
};

export type ResearchProposalTopicDecision = {
  decision: string;
  targetTopicId?: string | null;
  targetTopicTitle?: string | null;
  proposedTopicTitle?: string | null;
};

export type ResearchProposalClaim = {
  statement: string;
  citationLabel: string;
  sourceId?: string | null;
};

export type ResearchProposalEvidence = {
  sourceId: string;
  sourceTitle: string;
  sourceVaultPath?: string | null;
  locator?: string | null;
  excerpt: string;
};

export type ResearchDashboard = {
  summary: {
    activeTopics: number;
    pendingReviews: number;
    inboxSources: number;
    totalSources: number;
  };
  focusTopic: ResearchTopicSummary | null;
  recentSources: ResearchSourceRecord[];
  pendingReviews: ResearchReviewItem[];
  suggestedQuestions: string[];
};

export type ResearchTopicSourceLink = {
  sourceId: string;
  title: string;
  kind: ResearchSourceKind;
  locator?: string | null;
  vaultPath?: string | null;
  legacyNoteId?: string | null;
};

export type ResearchTopicClaim = {
  id: string;
  statement: string;
  sourceId?: string | null;
  citationLabel: string;
};

export type ResearchTopicThreadEntry = {
  id: string;
  role: ResearchThreadRole;
  content: string;
  sourceId?: string | null;
  createdAt: string;
};

export type ResearchTopicDetail = {
  id: string;
  title: string;
  summary: string;
  vaultPath?: string | null;
  contentHash?: string | null;
  currentUnderstanding: string[];
  openQuestions: string[];
  sources: ResearchTopicSourceLink[];
  keyClaims: ResearchTopicClaim[];
  thread: ResearchTopicThreadEntry[];
  updatedAt: string;
};

export type ResearchAskCitation = {
  sourceId: string;
  title: string;
  kind: ResearchSourceKind;
  locator?: string | null;
  vaultPath?: string | null;
};

export type ResearchAskWebSource = {
  url: string;
  title: string;
  excerpt: string;
  reasonUsed: string;
};

export type ResearchAskRequest = {
  question: string;
  topicId?: string;
  mode?: ResearchAskMode;
  continueFromAskTurnId?: string;
};

export type ResearchAskHistoryEntry = {
  id: string;
  title: string;
  href: string;
  topicTitle?: string | null;
  preview: string;
  updatedAt: string;
};

export type ResearchWebImportRequest = {
  url: string;
  title?: string;
};

export type ResearchTextImportRequest = {
  title: string;
  locator?: string;
  excerpt?: string;
  body: string;
};

export type ResearchAskResponse = {
  id: string;
  topicId?: string | null;
  question: string;
  answer: string;
  confidence: number;
  followUpQuestions: string[];
  knowledgeGaps: string[];
  usedWikiIds: string[];
  usedSourceIds: string[];
  usedWebSources: ResearchAskWebSource[];
  contextAskTurnIds: string[];
  canWriteback: boolean;
  citations: ResearchAskCitation[];
  createdAt: string;
};
