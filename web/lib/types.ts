export type ResearchSourceKind = "TEXT" | "WEB" | "PDF" | "LEGACY_NOTE";

export type ResearchSourceStatus = "RAW" | "INGEST_PENDING" | "WIKI_LINKED" | "IGNORED";

export type ResearchReviewKind = "TOPIC_CREATE" | "TOPIC_PATCH";

export type ResearchProposalKind = "TOPIC_CREATE" | "TOPIC_PATCH";

export type ResearchThreadRole = "USER" | "ASSISTANT" | "SYSTEM";

export type ResearchAskMode = "vault" | "vault_plus_web";

export type ResearchClaimProvenanceStatus = "supported" | "partial" | "unsupported";

export type ResearchHealthSignalType =
  | "RAW_BACKLOG"
  | "REVIEW_BACKLOG"
  | "OPEN_QUESTIONS"
  | "KNOWLEDGE_GAP"
  | "UNSUPPORTED_CLAIM"
  | "STALE_CLAIM"
  | "CONFLICTING_CLAIM"
  | "WRITEBACK_CANDIDATE";

export type ResearchHealthSignalSeverity = "info" | "warning" | "critical";

export type ResearchTopicSummary = {
  id: string;
  title: string;
  summary: string;
  sourceCount: number;
  openQuestionCount: number;
  unsupportedClaimCount: number;
  staleClaimCount: number;
  conflictingClaimCount: number;
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
  citationChunkIds?: string[];
  supportingChunkIds?: string[];
  evidenceCount?: number;
  provenanceStatus?: ResearchClaimProvenanceStatus;
  lastVerifiedAt?: string | null;
  usageCount?: number;
  lastUsedAt?: string | null;
  needsReview?: boolean;
  hasConflict?: boolean;
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
  health: {
    rawBacklogCount: number;
    reviewBacklogCount: number;
    openQuestionCount: number;
    knowledgeGapCount: number;
    writebackCandidateCount: number;
    unsupportedClaimCount: number;
    staleClaimCount: number;
    conflictingClaimCount: number;
    signals: ResearchHealthSignal[];
  };
  focusTopic: ResearchTopicSummary | null;
  recentSources: ResearchSourceRecord[];
  pendingReviews: ResearchReviewItem[];
  suggestedQuestions: string[];
};

export type ResearchHealthSignal = {
  type: ResearchHealthSignalType;
  severity: ResearchHealthSignalSeverity;
  title: string;
  summary: string;
  relatedId?: string | null;
  relatedTitle?: string | null;
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
  evidenceCount?: number;
  provenanceStatus?: ResearchClaimProvenanceStatus;
  lastVerifiedAt?: string | null;
  usageCount?: number;
  lastUsedAt?: string | null;
  needsReview?: boolean;
  hasConflict?: boolean;
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
  id?: string;
  entityType?: string;
  entityId?: string;
  sourceId?: string | null;
  topicId?: string | null;
  title: string;
  kind?: ResearchSourceKind;
  locator?: string | null;
  vaultPath?: string | null;
  snippet?: string;
  chunkId?: string;
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
  runId?: string;
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
  parentAskTurnId?: string | null;
  threadRootAskTurnId?: string;
  lineageAskTurnIds?: string[];
  question: string;
  answer: string;
  confidence: number;
  retrievalMode?: string;
  usedChunkIds?: string[];
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

export type ResearchReviewDecision = {
  reviewId: string;
  status: string;
  topicId?: string | null;
};

export type ResearchAskBriefingScope = "workspace" | "topic" | "ask_turn";

export type ResearchAskBriefingGap = {
  title: string;
  detail: string;
  href: string;
};

export type ResearchAskBriefingAction = {
  kind: string;
  label: string;
  description: string;
  href: string;
};

export type ResearchAskBriefingSignal = {
  type: string;
  title: string;
  summary: string;
  href: string;
};

export type ResearchAskBriefing = {
  scope: ResearchAskBriefingScope;
  topicId?: string | null;
  topicTitle?: string | null;
  askTurnId?: string | null;
  summary: string;
  confidence: number;
  knowledgeGaps: ResearchAskBriefingGap[];
  nextActions: ResearchAskBriefingAction[];
  suggestedQuestions: string[];
  supportingSignals: ResearchAskBriefingSignal[];
  generatedAt: string;
};

export type VaultStatus = {
  initialized: boolean;
  vaultType: string | null;
  sharedDirsExist: boolean;
};

export type VaultInitializeRequest = {
  vaultType: string;
};

export type DevRunType = "PRD" | "BUG" | "REFACTOR";

export type DevRunStatus = "draft" | "active" | "awaiting_review" | "blocked" | "completed" | "cancelled";

export type DevRunStageStatus = "pending" | "active" | "awaiting_review" | "completed" | "blocked" | "skipped";

export type DevRunStage = {
  name: string;
  status: DevRunStageStatus;
};

export type DevRunEvent = {
  id: string;
  eventType: string;
  stage?: string | null;
  payload: Record<string, unknown>;
  createdAt: string;
};

export type DevRun = {
  id: string;
  workspaceId: string;
  type: DevRunType;
  title: string;
  goal: string;
  repoContext?: string | null;
  status: DevRunStatus;
  currentStage: string;
  stageStatus: DevRunStageStatus;
  stages: DevRunStage[];
  events: DevRunEvent[];
  createdAt: string;
  updatedAt?: string | null;
  completedAt?: string | null;
  cancelledAt?: string | null;
};

export type DevRunSummary = {
  id: string;
  type: DevRunType;
  title: string;
  status: DevRunStatus;
  currentStage: string;
  stageStatus: DevRunStageStatus;
  createdAt: string;
};

export type CreateDevRunRequest = {
  type: DevRunType;
  title: string;
  goal: string;
  repoContext?: string;
};