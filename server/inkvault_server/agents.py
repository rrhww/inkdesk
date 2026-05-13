from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable, TypedDict

from pydantic import BaseModel, Field, field_validator

from inkvault_server.core.config import Settings

try:
    from langchain_openai import ChatOpenAI
    from langgraph.graph import END, START, StateGraph
    try:
        import langchain
    except Exception:  # pragma: no cover
        langchain = None  # type: ignore[assignment]
    if langchain is not None:
        if not hasattr(langchain, "debug"):
            langchain.debug = False
        if not hasattr(langchain, "verbose"):
            langchain.verbose = False
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[assignment]
    END = "END"  # type: ignore[assignment]
    START = "START"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


REVIEW_CARD_TITLE_BY_KIND = {
    "TOPIC_CREATE": "从 raw 建立 wiki 页面",
    "TOPIC_PATCH": "把 raw 编译进现有 wiki",
}

BRIEFING_SIGNAL_PRIORITY = {
    "UNSUPPORTED_CLAIM": 0,
    "STALE_CLAIM": 1,
    "CONFLICTING_CLAIM": 2,
    "KNOWLEDGE_GAP": 3,
    "OPEN_QUESTIONS": 4,
    "REVIEW_BACKLOG": 5,
    "RAW_BACKLOG": 6,
    "WRITEBACK_CANDIDATE": 7,
}


def ensure_langchain_runtime_globals() -> None:
    if langchain is None:
        return
    if not hasattr(langchain, "debug"):
        langchain.debug = False
    if not hasattr(langchain, "verbose"):
        langchain.verbose = False
    if not hasattr(langchain, "llm_cache"):
        langchain.llm_cache = None


ASK_JSON_MODE_INSTRUCTIONS = (
    "Return only valid JSON. "
    "The JSON object must contain exactly these keys: "
    "answer, confidence, followUpQuestions, knowledgeGaps, citationSourceIds."
)

BRIEFING_JSON_MODE_INSTRUCTIONS = (
    "Return only valid JSON. "
    "The JSON object must contain exactly these keys: "
    "summary, confidence, knowledgeGaps, nextActions, suggestedQuestions, supportingSignals."
)

COMPILE_JSON_MODE_INSTRUCTIONS = (
    "Return only valid JSON. "
    "The JSON object must contain exactly these keys: "
    "kind, title, summary, proposedTopicTitle, proposedUnderstanding, proposedOpenQuestions, proposedClaim, "
    "summaryChanges, claims, conflicts, openQuestions, evidenceCitationIds, explanation."
)

COMPILE_STYLE_INSTRUCTIONS = (
    "Respond in Simplified Chinese. "
    "The `title` field is the review card title, not the wiki topic title. "
    "Use exactly `从 raw 建立 wiki 页面` for `TOPIC_CREATE`, and exactly `把 raw 编译进现有 wiki` for `TOPIC_PATCH`. "
    "Keep `summary`, `proposedUnderstanding`, `proposedClaim`, and `proposedOpenQuestions` as short natural Chinese sentences without markdown, bullets, or English section labels. "
    "If `proposedTopicTitle` is needed, produce a stable Chinese topic name and avoid drifting into article headlines, source-site suffixes, or marketing wording."
)


class TopicModel(BaseModel):
    id: str
    title: str
    currentUnderstanding: list[str] = []
    openQuestions: list[str] = []
    summary: str | None = None
    vaultPath: str | None = None


class CitationModel(BaseModel):
    id: str
    title: str
    kind: str
    excerpt: str
    locator: str | None = None
    vaultPath: str | None = None


class SourceModel(BaseModel):
    id: str
    title: str
    kind: str
    excerpt: str
    body: str
    locator: str | None = None
    vaultPath: str | None = None


class AskContextTurnModel(BaseModel):
    askTurnId: str
    question: str
    answer: str


class WebCitationModel(BaseModel):
    url: str
    title: str
    excerpt: str
    reasonUsed: str


class AskWritebackPackageModel(BaseModel):
    topicDecision: str
    targetTopicId: str | None = None
    proposedTopicTitle: str | None = None
    proposedUnderstanding: str
    proposedClaim: str
    proposedOpenQuestion: str
    usedWebSources: list[WebCitationModel] = Field(default_factory=list)


class AskRequestModel(BaseModel):
    question: str
    mode: str
    pendingReviewCount: int
    topic: TopicModel | None = None
    citations: list[CitationModel] = Field(default_factory=list)
    contextTurns: list[AskContextTurnModel] = Field(default_factory=list)
    continueFromAskTurnId: str | None = None


class AskResponseModel(BaseModel):
    answer: str
    confidence: float
    followUpQuestions: list[str]
    knowledgeGaps: list[str]
    citationSourceIds: list[str]
    usedWebSources: list[WebCitationModel] = Field(default_factory=list)
    contextAskTurnIds: list[str] = Field(default_factory=list)
    canWriteback: bool = True
    writebackPackage: AskWritebackPackageModel | None = None


class AskBriefingSignalModel(BaseModel):
    type: str
    title: str
    summary: str
    href: str


class AskBriefingGapModel(BaseModel):
    title: str
    detail: str
    href: str


class AskBriefingActionModel(BaseModel):
    kind: str
    label: str
    description: str
    href: str


class AskBriefingRequestModel(BaseModel):
    scope: str
    topicId: str | None = None
    topicTitle: str | None = None
    askTurnId: str | None = None
    askQuestion: str | None = None
    askAnswer: str | None = None
    askKnowledgeGaps: list[str] = Field(default_factory=list)
    askUsedWebSources: list[WebCitationModel] = Field(default_factory=list)
    canWriteback: bool = False
    pendingReviewCount: int = 0
    focusTopicTitle: str | None = None
    recentSourceTitles: list[str] = Field(default_factory=list)
    healthSignals: list[AskBriefingSignalModel] = Field(default_factory=list)
    citations: list[CitationModel] = Field(default_factory=list)
    suggestedQuestions: list[str] = Field(default_factory=list)


class AskBriefingResponseModel(BaseModel):
    scope: str
    topicId: str | None = None
    topicTitle: str | None = None
    askTurnId: str | None = None
    summary: str
    confidence: float
    knowledgeGaps: list[AskBriefingGapModel] = Field(default_factory=list)
    nextActions: list[AskBriefingActionModel] = Field(default_factory=list)
    suggestedQuestions: list[str] = Field(default_factory=list)
    supportingSignals: list[AskBriefingSignalModel] = Field(default_factory=list)


class CompileRequestModel(BaseModel):
    source: SourceModel
    matchedTopic: TopicModel | None = None
    citations: list[CitationModel] = Field(default_factory=list)


class CompileClaimModel(BaseModel):
    statement: str
    citationIds: list[str] = Field(default_factory=list)


class CompileResponseModel(BaseModel):
    kind: str
    title: str
    summary: str
    proposedTopicTitle: str | None = None
    proposedUnderstanding: str
    proposedOpenQuestions: str
    proposedClaim: str
    summaryChanges: list[str] = Field(default_factory=list)
    claims: list[CompileClaimModel] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    openQuestions: list[str] = Field(default_factory=list)
    evidenceCitationIds: list[str] = Field(default_factory=list)
    explanation: str | None = None


class AskState(TypedDict, total=False):
    request: AskRequestModel
    question: str
    mode: str
    prompt: str
    answer: str
    confidence: float
    follow_up_questions: list[str]
    knowledge_gaps: list[str]
    citation_source_ids: list[str]
    used_web_sources: list[WebCitationModel]
    context_ask_turn_ids: list[str]
    has_vault_evidence: bool
    needs_web_assist: bool
    web_assist_attempted: bool
    can_writeback: bool
    writeback_package: AskWritebackPackageModel | None


class CompileState(TypedDict, total=False):
    request: CompileRequestModel
    prompt: str
    kind: str
    title: str
    summary: str
    proposed_topic_title: str | None
    proposed_understanding: str
    proposed_open_questions: str
    proposed_claim: str
    summary_changes: list[str]
    claims: list[CompileClaimModel]
    conflicts: list[str]
    open_questions: list[str]
    evidence_citation_ids: list[str]
    explanation: str | None


class AskStructuredOutput(BaseModel):
    answer: str
    confidence: float
    followUpQuestions: list[str]
    knowledgeGaps: list[str]
    citationSourceIds: list[str]

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            mapping = {
                "high": 0.85,
                "medium": 0.65,
                "low": 0.35,
            }
            if normalized in mapping:
                return mapping[normalized]
            try:
                return float(normalized)
            except ValueError:
                return 0.5
        return 0.5


class AskBriefingGapStructuredOutput(BaseModel):
    title: str
    detail: str
    href: str


class AskBriefingActionStructuredOutput(BaseModel):
    kind: str
    label: str
    description: str
    href: str


class AskBriefingStructuredOutput(BaseModel):
    summary: str
    confidence: float
    knowledgeGaps: list[AskBriefingGapStructuredOutput] = Field(default_factory=list)
    nextActions: list[AskBriefingActionStructuredOutput] = Field(default_factory=list)
    suggestedQuestions: list[str] = Field(default_factory=list)
    supportingSignals: list[AskBriefingSignalModel] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: Any) -> float:
        return AskStructuredOutput.normalize_confidence(value)


class CompileStructuredOutput(BaseModel):
    kind: str
    title: str
    summary: str
    proposedTopicTitle: str | None = None
    proposedUnderstanding: str
    proposedOpenQuestions: str
    proposedClaim: str
    summaryChanges: list[str] = Field(default_factory=list)
    claims: list[CompileClaimModel] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    openQuestions: list[str] = Field(default_factory=list)
    evidenceCitationIds: list[str] = Field(default_factory=list)
    explanation: str | None = None

    @field_validator("proposedOpenQuestions", mode="before")
    @classmethod
    def normalize_open_questions(cls, value: Any) -> str:
        if isinstance(value, list):
            return "；".join(str(item).strip() for item in value if str(item).strip())
        if value is None:
            return ""
        return str(value).strip()


def first_non_empty(items: list[str], fallback: str) -> str:
    for item in items:
        if item and item.strip():
            return item.strip()
    return fallback


def first_sentence(value: str, fallback: str = "等待补充更多来源。") -> str:
    text = (value or "").strip() or fallback
    boundaries = [index for index in (text.find("。"), text.find("."), text.find("!"), text.find("！"), text.find("?"), text.find("？")) if index >= 0]
    if not boundaries:
        return text
    return text[: min(boundaries) + 1].strip()


def suggest_open_question(kind: str) -> str:
    if kind == "LEGACY_NOTE":
        return "这条迁移材料在新 wiki 结构里应该扮演什么角色？"
    if kind == "PDF":
        return "这份 PDF 提供了哪些值得固化进 wiki 的证据？"
    return "这条新来源应该如何改变当前 wiki 理解？"


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def collapse_whitespace(value: str) -> str:
    return " ".join((value or "").split()).strip()


def clean_generated_text(value: str | None) -> str:
    text = collapse_whitespace(value or "")
    text = text.lstrip("-*").strip()
    return text.strip("`\"'“”‘’")


def strip_source_suffix(title: str) -> str:
    text = clean_generated_text(title)
    for marker in (" | ", " · "):
        if marker in text:
            text = text.split(marker, 1)[0].strip()
    return text


def should_fallback_to_source_language(candidate: str, source_text: str) -> bool:
    return bool(source_text.strip()) and has_cjk(source_text) and not has_cjk(candidate)


@dataclass
class AgentRuntime:
    settings: Settings
    web_assist_provider: Callable[[str], list[Any]] | None = None

    def __post_init__(self) -> None:
        ensure_langchain_runtime_globals()
        self._ask_llm = self._build_ask_llm()
        self._compile_llm = self._build_compile_llm()
        self._briefing_llm = self._build_briefing_llm()
        if StateGraph is None:
            self._ask_graph = None
            self._compile_graph = None
        else:
            self._ask_graph = self._build_ask_graph()
            self._compile_graph = self._build_compile_graph()

    def answer(self, request: AskRequestModel) -> AskResponseModel:
        if self._ask_graph is None:
            return self._deterministic_ask(request)
        state = self._ask_graph.invoke({"request": request})
        return AskResponseModel(
            answer=state["answer"],
            confidence=state["confidence"],
            followUpQuestions=state["follow_up_questions"],
            knowledgeGaps=state["knowledge_gaps"],
            citationSourceIds=state["citation_source_ids"],
            usedWebSources=state.get("used_web_sources", []),
            contextAskTurnIds=state.get("context_ask_turn_ids", self._context_ask_turn_ids(request)),
            canWriteback=state.get("can_writeback", True),
            writebackPackage=state.get("writeback_package"),
        )

    def brief(self, request: AskBriefingRequestModel) -> AskBriefingResponseModel:
        if self._briefing_llm is None:
            return self._deterministic_briefing(request)
        prompt = self._render_briefing_prompt(request)
        try:
            result = self._briefing_llm.invoke(prompt)
            return AskBriefingResponseModel(
                scope=request.scope,
                topicId=request.topicId,
                topicTitle=request.topicTitle,
                askTurnId=request.askTurnId,
                summary=result.summary,
                confidence=result.confidence,
                knowledgeGaps=[
                    AskBriefingGapModel(
                        title=item.title,
                        detail=item.detail,
                        href=item.href,
                    )
                    for item in result.knowledgeGaps
                ],
                nextActions=[
                    AskBriefingActionModel(
                        kind=item.kind,
                        label=item.label,
                        description=item.description,
                        href=item.href,
                    )
                    for item in result.nextActions
                ],
                suggestedQuestions=result.suggestedQuestions,
                supportingSignals=result.supportingSignals,
            )
        except Exception:
            logger.exception("Briefing LLM invocation failed; falling back to deterministic briefing.")
            return self._deterministic_briefing(request)

    def compile(self, request: CompileRequestModel) -> CompileResponseModel:
        if self._compile_llm is None or self._compile_graph is None:
            return self._deterministic_compile(request)
        state = self._compile_graph.invoke({"request": request})
        return CompileResponseModel(
            kind=state["kind"],
            title=state["title"],
            summary=state["summary"],
            proposedTopicTitle=state["proposed_topic_title"],
            proposedUnderstanding=state["proposed_understanding"],
            proposedOpenQuestions=state["proposed_open_questions"],
            proposedClaim=state["proposed_claim"],
            summaryChanges=state.get("summary_changes", []),
            claims=state.get("claims", []),
            conflicts=state.get("conflicts", []),
            openQuestions=state.get("open_questions", []),
            evidenceCitationIds=state.get("evidence_citation_ids", []),
            explanation=state.get("explanation"),
        )

    def _build_ask_llm(self):
        return self._build_structured_llm(AskStructuredOutput)

    def _build_briefing_llm(self):
        return self._build_structured_llm(AskBriefingStructuredOutput)

    def _build_compile_llm(self):
        return self._build_structured_llm(CompileStructuredOutput)

    def _build_structured_llm(self, schema: type[BaseModel]):
        provider = self.settings.resolved_agent_provider
        if ChatOpenAI is None or not provider.api_key or self.settings.agent_runtime == "deterministic":
            return None
        method = self._structured_output_method()
        llm = ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url,
            temperature=0.1,
            timeout=(
                self.settings.agent_connect_timeout_seconds,
                self.settings.agent_read_timeout_seconds,
            ),
        )
        return llm.with_structured_output(schema, method=method)

    def _build_ask_graph(self):
        graph = StateGraph(AskState)
        graph.add_node("load_request_context", self._load_request_context)
        graph.add_node("retrieve_vault_context", self._retrieve_vault_context)
        graph.add_node("compose_answer", self._compose_answer)
        graph.add_node("assess_evidence", self._assess_evidence)
        graph.add_node("optional_web_assist", self._optional_web_assist)
        graph.add_node("compose_answer_with_web", self._compose_answer)
        graph.add_node("build_writeback_package", self._build_writeback_package)
        graph.add_edge(START, "load_request_context")
        graph.add_edge("load_request_context", "retrieve_vault_context")
        graph.add_edge("retrieve_vault_context", "compose_answer")
        graph.add_edge("compose_answer", "assess_evidence")
        graph.add_conditional_edges(
            "assess_evidence",
            self._route_after_assessment,
            {
                "web": "optional_web_assist",
                "answer": "build_writeback_package",
            },
        )
        graph.add_edge("optional_web_assist", "compose_answer_with_web")
        graph.add_edge("compose_answer_with_web", "build_writeback_package")
        graph.add_edge("build_writeback_package", END)
        return graph.compile()

    def _build_compile_graph(self):
        graph = StateGraph(CompileState)
        graph.add_node("prepare_prompt", self._prepare_compile_prompt)
        graph.add_node("generate_proposal", self._generate_compile_proposal)
        graph.add_edge(START, "prepare_prompt")
        graph.add_edge("prepare_prompt", "generate_proposal")
        graph.add_edge("generate_proposal", END)
        return graph.compile()

    def _load_request_context(self, state: AskState) -> dict[str, Any]:
        request = state["request"]
        return {
            "question": request.question.strip(),
            "mode": request.mode,
            "context_ask_turn_ids": self._context_ask_turn_ids(request),
            "used_web_sources": [],
            "web_assist_attempted": False,
        }

    def _retrieve_vault_context(self, state: AskState) -> dict[str, Any]:
        request = state["request"]
        return {
            "citation_source_ids": [citation.id for citation in request.citations],
            "has_vault_evidence": self._has_vault_evidence(request),
        }

    def _assess_evidence(self, state: AskState) -> dict[str, Any]:
        request = state["request"]
        has_vault_evidence = state.get("has_vault_evidence", self._has_vault_evidence(request))
        needs_web_assist = (
            request.mode == "vault_plus_web"
            and self.web_assist_provider is not None
            and not state.get("web_assist_attempted", False)
            and (not has_vault_evidence or bool(state.get("knowledge_gaps", [])))
        )
        return {"needs_web_assist": needs_web_assist}

    def _route_after_assessment(self, state: AskState) -> str:
        if state["request"].mode == "vault_plus_web" and state.get("needs_web_assist"):
            return "web"
        return "answer"

    def _optional_web_assist(self, state: AskState) -> dict[str, Any]:
        if self.web_assist_provider is None:
            return {
                "used_web_sources": state.get("used_web_sources", []),
                "web_assist_attempted": True,
            }
        try:
            results = self.web_assist_provider(state["question"])
        except Exception:
            logger.exception("Web assist provider failed; continuing without external evidence.")
            return {"used_web_sources": [], "web_assist_attempted": True}

        used_web_sources: list[WebCitationModel] = []
        seen_urls: set[str] = set()
        for item in results:
            source = self._to_web_citation(item)
            if source is None or source.url in seen_urls:
                continue
            seen_urls.add(source.url)
            used_web_sources.append(source)
        return {
            "used_web_sources": used_web_sources,
            "web_assist_attempted": True,
        }

    def _compose_answer(self, state: AskState) -> dict[str, Any]:
        request = state["request"]
        prompt = self._render_ask_prompt(request, state.get("used_web_sources", []))
        if self._ask_llm is None:
            response = self._deterministic_ask(request, state.get("used_web_sources", []))
        else:
            try:
                result = self._ask_llm.invoke(prompt)
                response = AskResponseModel(
                    answer=result.answer,
                    confidence=result.confidence,
                    followUpQuestions=result.followUpQuestions,
                    knowledgeGaps=result.knowledgeGaps,
                    citationSourceIds=result.citationSourceIds,
                    usedWebSources=state.get("used_web_sources", []),
                    contextAskTurnIds=state.get("context_ask_turn_ids", self._context_ask_turn_ids(request)),
                    canWriteback=True,
                    writebackPackage=None,
                )
            except Exception:
                logger.exception("Ask LLM invocation failed; falling back to deterministic answer.")
                response = self._deterministic_ask(request, state.get("used_web_sources", [])).model_copy(
                    update={
                        "usedWebSources": state.get("used_web_sources", []),
                        "contextAskTurnIds": state.get(
                            "context_ask_turn_ids",
                            self._context_ask_turn_ids(request),
                        ),
                    }
                )
        return {
            "prompt": prompt,
            "answer": response.answer,
            "confidence": response.confidence,
            "follow_up_questions": response.followUpQuestions,
            "knowledge_gaps": response.knowledgeGaps,
            "citation_source_ids": response.citationSourceIds,
            "used_web_sources": response.usedWebSources,
            "context_ask_turn_ids": response.contextAskTurnIds,
            "can_writeback": response.canWriteback,
            "writeback_package": response.writebackPackage,
        }

    def _build_writeback_package(self, state: AskState) -> dict[str, Any]:
        if state.get("writeback_package") is not None:
            return {
                "writeback_package": state["writeback_package"],
                "can_writeback": state.get("can_writeback", True),
            }
        request = state["request"]
        answer = state["answer"]
        knowledge_gaps = state.get("knowledge_gaps", [])
        follow_up_questions = state.get("follow_up_questions", [])
        writeback_package = AskWritebackPackageModel(
            topicDecision="PATCH" if request.topic else "CREATE",
            targetTopicId=request.topic.id if request.topic else None,
            proposedTopicTitle=None if request.topic else first_sentence(request.question, fallback="新主题"),
            proposedUnderstanding=answer,
            proposedClaim=first_sentence(answer),
            proposedOpenQuestion=first_non_empty(
                knowledge_gaps + follow_up_questions,
                "围绕这个问题还需要补哪些来源？",
            ),
            usedWebSources=state.get("used_web_sources", []),
        )
        return {
            "writeback_package": writeback_package,
            "can_writeback": state.get("can_writeback", True),
        }

    def _render_ask_prompt(self, request: AskRequestModel, used_web_sources: list[WebCitationModel] | None = None) -> str:
        lines = [
            "You are the research agent for Inkvault.",
            "Answer from the vault-first perspective.",
            "Respond in Simplified Chinese, but preserve product names, URLs, and proper nouns in their original spelling when needed.",
            f"Mode: {request.mode}",
            f"Pending review count: {request.pendingReviewCount}",
            f"Question: {request.question}",
        ]
        if self._structured_output_method() == "json_mode":
            lines.append(ASK_JSON_MODE_INSTRUCTIONS)
        if request.topic:
            lines.extend(
                [
                    f"Topic title: {request.topic.title}",
                    "Current understanding:",
                    *[f"- {item}" for item in request.topic.currentUnderstanding],
                    "Open questions:",
                    *[f"- {item}" for item in request.topic.openQuestions],
                ]
            )
        if request.citations:
            lines.append("Available citations:")
            lines.extend(f"- [{citation.id}] {citation.title}: {citation.excerpt}" for citation in request.citations)
        if request.continueFromAskTurnId:
            lines.append(f"Continue from ask turn: {request.continueFromAskTurnId}")
        if request.contextTurns:
            lines.append("Context turns:")
            lines.extend(
                f"- [{turn.askTurnId}] Q: {turn.question} | A: {turn.answer}"
                for turn in request.contextTurns
            )
        if used_web_sources:
            lines.append("External web evidence:")
            lines.extend(
                f"- {source.title} ({source.url}): {source.excerpt} | Reason: {source.reasonUsed}"
                for source in used_web_sources
            )
        return "\n".join(lines)

    def _render_briefing_prompt(self, request: AskBriefingRequestModel) -> str:
        lines = [
            "You are the judgment hub for the Ask-first Inkvault workspace.",
            "Summarize the current research situation in Simplified Chinese.",
            "Focus on knowledge gaps and next safe actions.",
            f"Briefing scope: {request.scope}",
            BRIEFING_JSON_MODE_INSTRUCTIONS if self._structured_output_method() == "json_mode" else "",
        ]
        if request.topicTitle:
            lines.append(f"Topic title: {request.topicTitle}")
        if request.focusTopicTitle:
            lines.append(f"Focus topic: {request.focusTopicTitle}")
        if request.askTurnId:
            lines.append(f"Ask turn id: {request.askTurnId}")
        if request.askQuestion:
            lines.append(f"Ask question: {request.askQuestion}")
        if request.askAnswer:
            lines.append(f"Ask answer: {request.askAnswer}")
        if request.askKnowledgeGaps:
            lines.append("Ask knowledge gaps:")
            lines.extend(f"- {gap}" for gap in request.askKnowledgeGaps)
        if request.askUsedWebSources:
            lines.append("Ask external web evidence:")
            lines.extend(f"- {source.title}: {source.excerpt}" for source in request.askUsedWebSources)
        lines.append(f"Pending review count: {request.pendingReviewCount}")
        if request.recentSourceTitles:
            lines.append("Recent sources:")
            lines.extend(f"- {title}" for title in request.recentSourceTitles)
        if request.healthSignals:
            lines.append("Health signals:")
            lines.extend(f"- [{signal.type}] {signal.title}: {signal.summary} ({signal.href})" for signal in request.healthSignals)
        if request.citations:
            lines.append("Available citations:")
            lines.extend(f"- [{citation.id}] {citation.title}: {citation.excerpt}" for citation in request.citations)
        if request.suggestedQuestions:
            lines.append("Suggested questions:")
            lines.extend(f"- {item}" for item in request.suggestedQuestions)
        lines.append(f"Can write back: {'yes' if request.canWriteback else 'no'}")
        return "\n".join(line for line in lines if line)

    def _prepare_compile_prompt(self, state: CompileState) -> dict[str, Any]:
        request = state["request"]
        lines = [
            "You are compiling a research proposal for Inkvault.",
            "Inkvault is a vault-first private LLM Wiki with a raw -> ingest -> wiki review loop.",
            "You are writing a reviewable ingest proposal, not editing the wiki directly.",
            COMPILE_STYLE_INSTRUCTIONS,
            COMPILE_JSON_MODE_INSTRUCTIONS if self._structured_output_method() == "json_mode" else "",
            f"Source title: {request.source.title}",
            f"Source kind: {request.source.kind}",
            f"Source excerpt: {request.source.excerpt}",
            f"Source body: {request.source.body}",
        ]
        if request.matchedTopic:
            lines.extend(
                [
                    f"Matched topic: {request.matchedTopic.title}",
                    f"Topic summary: {request.matchedTopic.summary or ''}",
                    "Prefer TOPIC_PATCH when this source clearly extends the matched topic. Only use TOPIC_CREATE if it introduces a genuinely different canonical topic.",
                    "Current understanding:",
                    *[f"- {item}" for item in request.matchedTopic.currentUnderstanding],
                ]
            )
        else:
            lines.append("If you choose TOPIC_CREATE, keep the new topic title stable and avoid copying source-site branding.")
        if request.citations:
            lines.append("Retrieved context:")
            lines.extend(f"- [{citation.id}] {citation.title}: {citation.excerpt}" for citation in request.citations)
        return {"prompt": "\n".join(line for line in lines if line)}

    def _generate_compile_proposal(self, state: CompileState) -> dict[str, Any]:
        request = state["request"]
        if self._compile_llm is None:
            response = self._deterministic_compile(request)
            normalized = self._normalize_compile_response(request, response)
            return {
                "kind": normalized.kind,
                "title": normalized.title,
                "summary": normalized.summary,
                "proposed_topic_title": normalized.proposedTopicTitle,
                "proposed_understanding": normalized.proposedUnderstanding,
                "proposed_open_questions": normalized.proposedOpenQuestions,
                "proposed_claim": normalized.proposedClaim,
                "summary_changes": normalized.summaryChanges,
                "claims": normalized.claims,
                "conflicts": normalized.conflicts,
                "open_questions": normalized.openQuestions,
                "evidence_citation_ids": normalized.evidenceCitationIds,
                "explanation": normalized.explanation,
            }
        try:
            result = self._compile_llm.invoke(state["prompt"])
        except Exception:
            logger.exception("Compile LLM invocation failed; falling back to deterministic proposal.")
            response = self._deterministic_compile(request)
            normalized = self._normalize_compile_response(request, response)
            return {
                "kind": normalized.kind,
                "title": normalized.title,
                "summary": normalized.summary,
                "proposed_topic_title": normalized.proposedTopicTitle,
                "proposed_understanding": normalized.proposedUnderstanding,
                "proposed_open_questions": normalized.proposedOpenQuestions,
                "proposed_claim": normalized.proposedClaim,
                "summary_changes": normalized.summaryChanges,
                "claims": normalized.claims,
                "conflicts": normalized.conflicts,
                "open_questions": normalized.openQuestions,
                "evidence_citation_ids": normalized.evidenceCitationIds,
                "explanation": normalized.explanation,
            }
        normalized = self._normalize_compile_response(
            request,
            CompileResponseModel(
                kind=result.kind,
                title=result.title,
                summary=result.summary,
                proposedTopicTitle=result.proposedTopicTitle,
                proposedUnderstanding=result.proposedUnderstanding,
                proposedOpenQuestions=result.proposedOpenQuestions,
                proposedClaim=result.proposedClaim,
                summaryChanges=result.summaryChanges,
                claims=result.claims,
                conflicts=result.conflicts,
                openQuestions=result.openQuestions,
                evidenceCitationIds=result.evidenceCitationIds,
                explanation=result.explanation,
            ),
        )
        return {
            "kind": normalized.kind,
            "title": normalized.title,
            "summary": normalized.summary,
            "proposed_topic_title": normalized.proposedTopicTitle,
            "proposed_understanding": normalized.proposedUnderstanding,
            "proposed_open_questions": normalized.proposedOpenQuestions,
            "proposed_claim": normalized.proposedClaim,
            "summary_changes": normalized.summaryChanges,
            "claims": normalized.claims,
            "conflicts": normalized.conflicts,
            "open_questions": normalized.openQuestions,
            "evidence_citation_ids": normalized.evidenceCitationIds,
            "explanation": normalized.explanation,
        }

    def _deterministic_ask(self, request: AskRequestModel, used_web_sources: list[WebCitationModel] | None = None) -> AskResponseModel:
        web_sources = used_web_sources or []
        citation_ids = [citation.id for citation in request.citations]
        if web_sources:
            external_excerpt = first_non_empty([source.excerpt for source in web_sources], "外部资料提供了补充证据。")
            external_follow_up = first_non_empty(
                [source.reasonUsed for source in web_sources] + [source.title for source in web_sources],
                "这条外部补料是否值得沉淀进 wiki？",
            )
            if request.topic:
                understanding = first_non_empty(request.topic.currentUnderstanding, "等待补充更多来源。")
                return AskResponseModel(
                    answer=f"基于当前 wiki，最稳定的理解仍然是：{understanding}。外部补料进一步显示：{external_excerpt}",
                    confidence=0.84,
                    followUpQuestions=[external_follow_up],
                    knowledgeGaps=[],
                    citationSourceIds=citation_ids,
                    usedWebSources=web_sources,
                    contextAskTurnIds=self._context_ask_turn_ids(request),
                    canWriteback=True,
                )
            titles = "；".join(source.title for source in web_sources)
            return AskResponseModel(
                answer=f"当前除了 vault 内材料，外部补料还提供了这些线索：{titles}。其中最直接的证据是：{external_excerpt}",
                confidence=0.76,
                followUpQuestions=[external_follow_up],
                knowledgeGaps=[],
                citationSourceIds=citation_ids,
                usedWebSources=web_sources,
                contextAskTurnIds=self._context_ask_turn_ids(request),
                canWriteback=True,
            )
        if request.topic:
            understanding = first_non_empty(request.topic.currentUnderstanding, "等待补充更多来源。")
            open_question = first_non_empty(request.topic.openQuestions, "下一步还需要补哪条证据？")
            return AskResponseModel(
                answer=f"当前最重要的理解是：{understanding}。接下来优先追问：{open_question}",
                confidence=0.86 if request.mode == "vault" else 0.79,
                followUpQuestions=[open_question],
                knowledgeGaps=[] if request.mode == "vault" else ["当前 wiki 还没有覆盖更广的外部资料。"],
                citationSourceIds=citation_ids,
                usedWebSources=[],
                contextAskTurnIds=self._context_ask_turn_ids(request),
                canWriteback=True,
            )
        titles = "；".join(citation.title for citation in request.citations) if request.citations else "暂无来源"
        return AskResponseModel(
            answer=f"当前还有 {request.pendingReviewCount} 条待审阅迁移项，最近的来源主要围绕：{titles}",
            confidence=0.7 if request.mode == "vault" else 0.62,
            followUpQuestions=["这些待审阅项里，哪一条最值得先确认进入长期记忆？"],
            knowledgeGaps=[
                "当前回答只覆盖 vault 内已导入的材料。"
                if request.mode == "vault"
                else "如果要回答得更完整，建议联网补料以补足 vault 外的最新细节。"
            ],
            citationSourceIds=citation_ids,
            usedWebSources=[],
            contextAskTurnIds=self._context_ask_turn_ids(request),
            canWriteback=True,
        )

    def _deterministic_briefing(self, request: AskBriefingRequestModel) -> AskBriefingResponseModel:
        knowledge_gaps: list[AskBriefingGapModel] = []
        next_actions: list[AskBriefingActionModel] = []
        prioritized_signals = sorted(
            request.healthSignals,
            key=lambda signal: BRIEFING_SIGNAL_PRIORITY.get(signal.type, 99),
        )

        if request.askKnowledgeGaps:
            for gap in request.askKnowledgeGaps[:3]:
                knowledge_gaps.append(
                    AskBriefingGapModel(
                        title=first_sentence(gap, "当前还有知识缺口。"),
                        detail=gap,
                        href="/app/ask" if request.scope == "workspace" else "/app",
                    )
                )

        if not knowledge_gaps:
            for signal in prioritized_signals[:3]:
                if signal.type in {"RAW_BACKLOG", "REVIEW_BACKLOG", "OPEN_QUESTIONS", "KNOWLEDGE_GAP", "UNSUPPORTED_CLAIM", "STALE_CLAIM", "CONFLICTING_CLAIM"}:
                    knowledge_gaps.append(
                        AskBriefingGapModel(
                            title=signal.title,
                            detail=signal.summary,
                            href=signal.href,
                        )
                    )

        if request.scope == "ask_turn":
            summary = first_non_empty(
                [
                    f"这轮问答已经得到一版可继续推进的判断：{first_sentence(request.askAnswer or '', '先从当前回答继续推进。')}",
                    request.askQuestion or "",
                ],
                "这轮问答已经形成一版可继续推进的判断。",
            )
            next_actions.append(
                AskBriefingActionModel(
                    kind="CONTINUE_ASK",
                    label="继续追问",
                    description="围绕这轮回答继续补证或缩小范围。",
                    href="/app/ask",
                )
            )
            if request.canWriteback:
                next_actions.append(
                    AskBriefingActionModel(
                        kind="WRITEBACK",
                        label="沉淀到知识库",
                        description="把这轮回答送入 ingest 审阅，而不是直接改写 wiki。",
                        href="/app/ask",
                    )
                )
        elif request.scope == "topic":
            summary = first_non_empty(
                [
                    f"当前主题「{request.topicTitle or request.focusTopicTitle or '未命名主题'}」最需要先补证再推进。",
                    prioritized_signals[0].title if prioritized_signals else "",
                ],
                "当前主题最需要先补证再推进。",
            )
            next_actions.append(
                AskBriefingActionModel(
                    kind="OPEN_WIKI",
                    label="打开知识页",
                    description="先查看当前主题的既有理解，再决定下一轮提问。",
                    href="/app/wiki",
                )
            )
        else:
            summary = first_non_empty(
                [
                    prioritized_signals[0].title if prioritized_signals else "",
                    f"当前最需要先处理 {request.pendingReviewCount} 条待审阅提案。",
                ],
                "当前最需要先看清知识缺口，再决定下一步动作。",
            )

        for signal in prioritized_signals:
            if len(next_actions) >= 3:
                break
            if signal.type == "REVIEW_BACKLOG" and not any(action.kind == "OPEN_INGEST" for action in next_actions):
                next_actions.append(
                    AskBriefingActionModel(
                        kind="OPEN_INGEST",
                        label="打开审阅队列",
                        description="先处理最靠前的提案，再继续扩展知识层。",
                        href=signal.href,
                    )
                )
            elif signal.type == "RAW_BACKLOG" and not any(action.kind == "OPEN_RAW" for action in next_actions):
                next_actions.append(
                    AskBriefingActionModel(
                        kind="OPEN_RAW",
                        label="补充资料入口",
                        description="回到 raw 检查哪些材料还没有进入 ingest。",
                        href=signal.href,
                    )
                )
            elif signal.type == "OPEN_QUESTIONS" and not any(action.kind == "OPEN_WIKI" for action in next_actions):
                next_actions.append(
                    AskBriefingActionModel(
                        kind="OPEN_WIKI",
                        label="查看开放问题",
                        description="先读当前 wiki 的开放问题，再决定追问方向。",
                        href=signal.href,
                    )
                )
            elif signal.type == "STALE_CLAIM" and not any(action.kind == "OPEN_INGEST" for action in next_actions):
                next_actions.append(
                    AskBriefingActionModel(
                        kind="OPEN_INGEST",
                        label="发起 claim 重审",
                        description="这些高频 claim 需要回到 ingest 做一轮复核，避免继续带着旧判断推进。",
                        href=signal.href,
                    )
                )
            elif signal.type == "CONFLICTING_CLAIM" and not any(action.kind == "OPEN_INGEST" for action in next_actions):
                next_actions.append(
                    AskBriefingActionModel(
                        kind="OPEN_INGEST",
                        label="处理 claim 冲突",
                        description="回到 ingest 统一裁决互相打架的 claim，避免继续带着冲突理解推进。",
                        href=signal.href,
                    )
                )

        if not next_actions:
            next_actions.append(
                AskBriefingActionModel(
                    kind="CONTINUE_ASK",
                    label="继续追问",
                    description="围绕当前问题继续缩小范围或补证。",
                    href="/app/ask",
                )
            )

        suggested_questions = request.suggestedQuestions[:3]
        if not suggested_questions:
            if request.askKnowledgeGaps:
                suggested_questions = [first_sentence(request.askKnowledgeGaps[0], "下一步最值得补哪条证据？")]
            elif request.focusTopicTitle:
                suggested_questions = [f"围绕「{request.focusTopicTitle}」下一步最值得补哪条证据？"]
            else:
                suggested_questions = ["当前哪条提案最值得先审阅？"]

        return AskBriefingResponseModel(
            scope=request.scope,
            topicId=request.topicId,
            topicTitle=request.topicTitle,
            askTurnId=request.askTurnId,
            summary=summary,
            confidence=0.86 if request.scope == "ask_turn" else 0.74,
            knowledgeGaps=knowledge_gaps[:3],
            nextActions=next_actions[:3],
            suggestedQuestions=suggested_questions[:3],
            supportingSignals=prioritized_signals[:3],
        )

    def _to_web_citation(self, item: Any) -> WebCitationModel | None:
        if isinstance(item, WebCitationModel):
            return item
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or url).strip()
            excerpt = str(item.get("excerpt") or "").strip()
            reason = str(item.get("reasonUsed") or item.get("reason_used") or "").strip()
            if not url or not excerpt:
                return None
            return WebCitationModel(url=url, title=title or url, excerpt=excerpt, reasonUsed=reason or "这条外部资料补足了 vault 当前的知识缺口。")
        if hasattr(item, "url") and hasattr(item, "title") and hasattr(item, "excerpt"):
            url = str(getattr(item, "url") or "").strip()
            title = str(getattr(item, "title") or url).strip()
            excerpt = str(getattr(item, "excerpt") or "").strip()
            reason = str(
                getattr(item, "reason_used", None)
                or getattr(item, "reasonUsed", None)
                or ""
            ).strip()
            if not url or not excerpt:
                return None
            return WebCitationModel(url=url, title=title or url, excerpt=excerpt, reasonUsed=reason or "这条外部资料补足了 vault 当前的知识缺口。")
        return None

    def _structured_output_method(self) -> str:
        return self.settings.agent_provider_structured_output_method

    def _normalize_compile_response(
        self,
        request: CompileRequestModel,
        response: CompileResponseModel,
    ) -> CompileResponseModel:
        normalized_kind = response.kind if response.kind in {"TOPIC_CREATE", "TOPIC_PATCH"} else ("TOPIC_PATCH" if request.matchedTopic else "TOPIC_CREATE")
        source_title = strip_source_suffix(request.source.title)
        source_excerpt = clean_generated_text(request.source.excerpt)
        summary = clean_generated_text(response.summary) or source_excerpt
        if should_fallback_to_source_language(summary, source_excerpt):
            summary = first_sentence(source_excerpt)
        proposed_understanding = clean_generated_text(response.proposedUnderstanding) or summary
        if should_fallback_to_source_language(proposed_understanding, source_excerpt):
            proposed_understanding = summary
        proposed_claim = clean_generated_text(response.proposedClaim) or first_sentence(proposed_understanding)
        if should_fallback_to_source_language(proposed_claim, source_excerpt):
            proposed_claim = first_sentence(summary)
        proposed_open_questions = clean_generated_text(response.proposedOpenQuestions) or suggest_open_question(request.source.kind)
        if should_fallback_to_source_language(proposed_open_questions, source_excerpt):
            proposed_open_questions = suggest_open_question(request.source.kind)
        available_citation_ids = {citation.id for citation in request.citations}
        summary_changes = [clean_generated_text(item) for item in response.summaryChanges if clean_generated_text(item)] or [summary]
        claims = [
            CompileClaimModel(
                statement=clean_generated_text(item.statement) or proposed_claim,
                citationIds=[citation_id for citation_id in item.citationIds if citation_id in available_citation_ids],
            )
            for item in response.claims
            if clean_generated_text(item.statement)
        ]
        if not claims and proposed_claim:
            claims = [
                CompileClaimModel(
                    statement=proposed_claim,
                    citationIds=[request.citations[0].id] if request.citations else [],
                )
            ]
        conflicts = [clean_generated_text(item) for item in response.conflicts if clean_generated_text(item)]
        open_questions = [clean_generated_text(item) for item in response.openQuestions if clean_generated_text(item)] or [proposed_open_questions]
        evidence_citation_ids = [citation_id for citation_id in response.evidenceCitationIds if citation_id in available_citation_ids]
        if not evidence_citation_ids:
            seen_ids: set[str] = set()
            evidence_citation_ids = []
            for claim in claims:
                for citation_id in claim.citationIds:
                    if citation_id in seen_ids:
                        continue
                    seen_ids.add(citation_id)
                    evidence_citation_ids.append(citation_id)
            if not evidence_citation_ids:
                evidence_citation_ids = [citation.id for citation in request.citations[:2]]
        explanation = clean_generated_text(response.explanation) or (
            f"系统建议补丁到「{request.matchedTopic.title}」，因为检索到的上下文与新来源最相关。"
            if request.matchedTopic
            else "系统建议建立新主题，因为现有检索上下文里没有更合适的承接页面。"
        )

        proposed_topic_title: str | None = None
        if normalized_kind == "TOPIC_CREATE":
            candidate_topic_title = strip_source_suffix(response.proposedTopicTitle or source_title)
            if should_fallback_to_source_language(candidate_topic_title, request.source.title):
                candidate_topic_title = source_title
            proposed_topic_title = candidate_topic_title or source_title or None

        return CompileResponseModel(
            kind=normalized_kind,
            title=REVIEW_CARD_TITLE_BY_KIND[normalized_kind],
            summary=summary,
            proposedTopicTitle=proposed_topic_title,
            proposedUnderstanding=proposed_understanding,
            proposedOpenQuestions=proposed_open_questions,
            proposedClaim=proposed_claim,
            summaryChanges=summary_changes,
            claims=claims,
            conflicts=conflicts,
            openQuestions=open_questions,
            evidenceCitationIds=evidence_citation_ids,
            explanation=explanation,
        )

    def _context_ask_turn_ids(self, request: AskRequestModel) -> list[str]:
        context_ids = [turn.askTurnId for turn in request.contextTurns]
        if request.continueFromAskTurnId and request.continueFromAskTurnId not in context_ids:
            return [request.continueFromAskTurnId, *context_ids]
        return context_ids

    def _has_vault_evidence(self, request: AskRequestModel) -> bool:
        if request.citations:
            return True
        if request.topic and (request.topic.currentUnderstanding or request.topic.summary):
            return True
        return False

    def _deterministic_compile(self, request: CompileRequestModel) -> CompileResponseModel:
        matched_topic = request.matchedTopic
        return CompileResponseModel(
            kind="TOPIC_PATCH" if matched_topic else "TOPIC_CREATE",
            title="把 raw 编译进现有 wiki" if matched_topic else "从 raw 建立 wiki 页面",
            summary=request.source.excerpt,
            proposedTopicTitle=None if matched_topic else request.source.title,
            proposedUnderstanding=request.source.excerpt,
            proposedOpenQuestions=suggest_open_question(request.source.kind),
            proposedClaim=first_sentence(request.source.excerpt),
            summaryChanges=[request.source.excerpt],
            claims=[
                CompileClaimModel(
                    statement=first_sentence(request.source.excerpt),
                    citationIds=[request.citations[0].id] if request.citations else [],
                )
            ]
            if request.source.excerpt
            else [],
            conflicts=[],
            openQuestions=[suggest_open_question(request.source.kind)],
            evidenceCitationIds=[citation.id for citation in request.citations[:2]],
            explanation=(
                f"系统建议补丁到「{matched_topic.title}」，因为检索到的上下文与新来源最相关。"
                if matched_topic
                else "系统建议建立新主题，因为现有检索上下文里没有更合适的承接页面。"
            ),
        )
