from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    code: str
    message: str

class VaultStatusResponse(BaseModel):
    initialized: bool
    vaultType: str | None = None
    sharedDirsExist: bool


class VaultInitializeRequest(BaseModel):
    vaultType: str


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthLoginResponse(BaseModel):
    sessionToken: str


class AuthMeResponse(BaseModel):
    userId: str
    username: str
    workspaceId: str
    workspaceName: str
    workspaceSlug: str


class CreateSourceRequest(BaseModel):
    kind: str = "TEXT"
    title: str | None = None
    locator: str | None = None
    excerpt: str | None = None
    body: str | None = None


class WebRawImportRequest(BaseModel):
    url: str
    title: str | None = None


class SourceResponse(BaseModel):
    id: str
    kind: str
    status: str
    title: str
    locator: str | None = None
    excerpt: str
    legacyNoteId: str | None = None
    vaultPath: str | None = None
    contentHash: str | None = None
    updatedAt: datetime


class ReviewDecisionResponse(BaseModel):
    reviewId: str
    status: str
    topicId: str | None = None


class ProposalTopicDecisionResponse(BaseModel):
    decision: str
    targetTopicId: str | None = None
    targetTopicTitle: str | None = None
    proposedTopicTitle: str | None = None


class ProposalClaimResponse(BaseModel):
    statement: str
    citationLabel: str
    sourceId: str | None = None
    citationChunkIds: list[str] = Field(default_factory=list)
    supportingChunkIds: list[str] = Field(default_factory=list)
    evidenceCount: int = 0
    provenanceStatus: str = "unsupported"
    lastVerifiedAt: datetime | None = None
    usageCount: int = 0
    lastUsedAt: datetime | None = None
    needsReview: bool = False
    hasConflict: bool = False


class ProposalEvidenceResponse(BaseModel):
    sourceId: str
    sourceTitle: str
    sourceVaultPath: str | None = None
    locator: str | None = None
    excerpt: str
    chunkId: str | None = None
    entityType: str | None = None
    entityId: str | None = None
    topicId: str | None = None


class ProposalPayloadResponse(BaseModel):
    topicDecision: ProposalTopicDecisionResponse
    summaryChanges: list[str]
    claims: list[ProposalClaimResponse]
    conflicts: list[str]
    openQuestions: list[str]
    explanation: str
    evidence: list[ProposalEvidenceResponse]


class ReviewItemResponse(BaseModel):
    id: str
    kind: str
    proposalKind: str
    status: str
    title: str
    summary: str
    sourceId: str | None = None
    sourceTitle: str | None = None
    targetTopicId: str | None = None
    targetTopicTitle: str | None = None
    proposedTopicTitle: str | None = None
    proposedUnderstanding: str | None = None
    proposedOpenQuestions: str | None = None
    proposedClaim: str | None = None
    proposedVaultPath: str | None = None
    sourceVaultPath: str | None = None
    proposalPayload: ProposalPayloadResponse
    createdAt: datetime


class TopicSummaryResponse(BaseModel):
    id: str
    title: str
    summary: str
    sourceCount: int
    openQuestionCount: int
    unsupportedClaimCount: int = 0
    staleClaimCount: int = 0
    conflictingClaimCount: int = 0
    vaultPath: str | None = None
    updatedAt: datetime


class TopicSourceLinkResponse(BaseModel):
    sourceId: str
    title: str
    kind: str
    locator: str | None = None
    vaultPath: str | None = None
    legacyNoteId: str | None = None


class TopicClaimResponse(BaseModel):
    id: str
    statement: str
    sourceId: str | None = None
    citationLabel: str
    evidenceCount: int = 0
    provenanceStatus: str = "unsupported"
    lastVerifiedAt: datetime | None = None
    usageCount: int = 0
    lastUsedAt: datetime | None = None
    needsReview: bool = False
    hasConflict: bool = False


class TopicThreadEntryResponse(BaseModel):
    id: str
    role: str
    content: str
    sourceId: str | None = None
    createdAt: datetime


class TopicDetailResponse(BaseModel):
    id: str
    title: str
    summary: str
    vaultPath: str | None = None
    contentHash: str | None = None
    currentUnderstanding: list[str]
    openQuestions: list[str]
    sources: list[TopicSourceLinkResponse]
    keyClaims: list[TopicClaimResponse]
    thread: list[TopicThreadEntryResponse]
    updatedAt: datetime


class ResearchDashboardSummary(BaseModel):
    activeTopics: int
    pendingReviews: int
    inboxSources: int
    totalSources: int


class ResearchHealthSignalResponse(BaseModel):
    type: str
    severity: str
    title: str
    summary: str
    relatedId: str | None = None
    relatedTitle: str | None = None


class ResearchDashboardHealthResponse(BaseModel):
    rawBacklogCount: int
    reviewBacklogCount: int
    openQuestionCount: int
    knowledgeGapCount: int
    writebackCandidateCount: int
    unsupportedClaimCount: int = 0
    staleClaimCount: int = 0
    conflictingClaimCount: int = 0
    signals: list[ResearchHealthSignalResponse]


class ResearchDashboardResponse(BaseModel):
    summary: ResearchDashboardSummary
    health: ResearchDashboardHealthResponse
    focusTopic: TopicSummaryResponse | None
    recentSources: list[SourceResponse]
    pendingReviews: list[ReviewItemResponse]
    suggestedQuestions: list[str]


class AskRequest(BaseModel):
    topicId: str | None = None
    question: str
    mode: str | None = "vault"
    continueFromAskTurnId: str | None = None
    runId: str | None = None


class AskCitationResponse(BaseModel):
    id: str
    entityType: str
    entityId: str
    sourceId: str | None = None
    topicId: str | None = None
    title: str
    locator: str | None = None
    vaultPath: str | None = None
    snippet: str
    chunkId: str


class AskWebSourceResponse(BaseModel):
    url: str
    title: str
    excerpt: str
    reasonUsed: str


class AskBriefingGapResponse(BaseModel):
    title: str
    detail: str
    href: str


class AskBriefingActionResponse(BaseModel):
    kind: str
    label: str
    description: str
    href: str


class AskBriefingSignalResponse(BaseModel):
    type: str
    title: str
    summary: str
    href: str


class AskBriefingResponse(BaseModel):
    scope: str
    topicId: str | None = None
    topicTitle: str | None = None
    askTurnId: str | None = None
    summary: str
    confidence: float
    knowledgeGaps: list[AskBriefingGapResponse]
    nextActions: list[AskBriefingActionResponse]
    suggestedQuestions: list[str]
    supportingSignals: list[AskBriefingSignalResponse]
    generatedAt: datetime


class AskResponse(BaseModel):
    id: str
    topicId: str | None = None
    parentAskTurnId: str | None = None
    threadRootAskTurnId: str
    lineageAskTurnIds: list[str]
    question: str
    answer: str
    confidence: float
    retrievalMode: str
    usedChunkIds: list[str]
    followUpQuestions: list[str]
    knowledgeGaps: list[str]
    usedWikiIds: list[str]
    usedSourceIds: list[str]
    usedWebSources: list[AskWebSourceResponse]
    contextAskTurnIds: list[str]
    canWriteback: bool
    citations: list[AskCitationResponse]
    createdAt: datetime


class AskThreadResponse(BaseModel):
    rootAskTurnId: str
    currentAskTurnId: str
    topicId: str | None = None
    turns: list[AskResponse]


class CreateDevRunRequest(BaseModel):
    type: str
    title: str
    goal: str
    repoContext: str | None = None


class StageInfo(BaseModel):
    name: str
    status: str


class RunEventResponse(BaseModel):
    id: str
    eventType: str
    stage: str | None = None
    payload: dict
    createdAt: datetime


class DevRunResponse(BaseModel):
    id: str
    workspaceId: str
    type: str
    title: str
    goal: str
    repoContext: str | None = None
    status: str
    currentStage: str
    stageStatus: str
    stages: list[StageInfo]
    events: list[RunEventResponse]
    createdAt: datetime
    updatedAt: datetime | None = None
    completedAt: datetime | None = None
    cancelledAt: datetime | None = None


class DevRunSummaryResponse(BaseModel):
    id: str
    type: str
    title: str
    status: str
    currentStage: str
    stageStatus: str
    createdAt: datetime


class AddRunEventRequest(BaseModel):
    stage: str | None = None
    eventType: str
    payload: dict = Field(default_factory=dict)


class DepositRequest(BaseModel):
    source: str
    runId: str | None = None
    askTurnId: str | None = None
    stage: str | None = None
    payload: dict = Field(default_factory=dict)


class DepositResponse(BaseModel):
    reviewId: str
    status: str
    source: str
    isNew: bool = True
