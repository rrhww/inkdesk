# Ask Researcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Inkdesk Ask from a thin prompt wrapper into a vault-first Ask Researcher that supports contextual follow-ups, conditional web assist, and reviewable writeback into `raw -> ingest -> wiki`.

**Architecture:** Keep a single Python main backend and a single Ask runtime boundary. Refactor Ask into a staged LangGraph flow with explicit context loading, vault retrieval, evidence assessment, optional web assist, answer composition, and writeback package generation. Persist Ask turns as reusable research snapshots so the frontend can continue a line of questioning and materialize web-backed writeback proposals without re-running the full research flow.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, LangGraph, httpx, BeautifulSoup, Next.js App Router, Playwright, pytest

---

### Task 1: Expand Ask contracts and persistence shape

**Files:**
- Modify: `server/inkdesk_server/models.py`
- Modify: `server/inkdesk_server/schemas.py`
- Modify: `web/lib/types.ts`
- Modify: `server/tests/test_research_api.py`

- [ ] **Step 1: Write failing backend API tests for the new Ask request/response shape**

Add assertions in `server/tests/test_research_api.py` for:

```python
topic_response = client.post(
    "/api/ask",
    json={
        "topicId": topic_id,
        "question": "继续展开这个主题的证据边界",
        "mode": "vault",
        "continueFromAskTurnId": previous_ask_id,
    },
)
payload = topic_response.json()
assert payload["contextAskTurnIds"] == [previous_ask_id]
assert payload["canWriteback"] is True
assert payload["usedWebSources"] == []
```

- [ ] **Step 2: Write failing frontend type-usage tests for the new Ask fields**

Extend `web/tests/research-api.test.tsx` with expectations like:

```tsx
assert.equal(answer.contextAskTurnIds[0], "ask-123");
assert.equal(answer.canWriteback, true);
assert.deepEqual(answer.usedWebSources, []);
```

- [ ] **Step 3: Run the focused tests and verify they fail for the right reason**

Run: `cd server && python -m pytest tests/test_research_api.py -k ask`
Expected: FAIL because `continueFromAskTurnId`, `contextAskTurnIds`, `usedWebSources`, or `canWriteback` are missing.

Run: `cd web && node --import tsx --test tests/research-api.test.tsx`
Expected: FAIL because TypeScript fixtures or response shapes do not yet include the new Ask fields.

- [ ] **Step 4: Extend the SQLAlchemy AskTurn model to hold research snapshot fields**

Update `server/inkdesk_server/models.py` so `AskTurn` grows from:

```python
class AskTurn(Base):
    __tablename__ = "ask_turns"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    citation_source_ids: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

to:

```python
class AskTurn(Base):
    __tablename__ = "ask_turns"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    parent_ask_turn_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("ask_turns.id", ondelete="SET NULL"), nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="vault")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    citation_source_ids: Mapped[str] = mapped_column(Text, nullable=False)
    used_wiki_ids: Mapped[str] = mapped_column(Text, nullable=False, default="")
    used_source_ids: Mapped[str] = mapped_column(Text, nullable=False, default="")
    used_web_sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    knowledge_gaps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    follow_up_questions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    writeback_package_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 5: Extend backend and frontend Ask schemas**

In `server/inkdesk_server/schemas.py`, grow:

```python
class AskRequest(BaseModel):
    topicId: str | None = None
    question: str
    mode: str | None = "vault"
```

into:

```python
class AskRequest(BaseModel):
    topicId: str | None = None
    question: str
    mode: str | None = "vault"
    continueFromAskTurnId: str | None = None
```

and grow:

```python
class AskResponse(BaseModel):
    id: str
    topicId: str | None = None
    question: str
    answer: str
    confidence: float
    followUpQuestions: list[str]
    knowledgeGaps: list[str]
    usedWikiIds: list[str]
    usedSourceIds: list[str]
    citations: list[AskCitationResponse]
    createdAt: datetime
```

into:

```python
class AskWebSourceResponse(BaseModel):
    url: str
    title: str
    excerpt: str
    reasonUsed: str


class AskResponse(BaseModel):
    id: str
    topicId: str | None = None
    question: str
    answer: str
    confidence: float
    followUpQuestions: list[str]
    knowledgeGaps: list[str]
    usedWikiIds: list[str]
    usedSourceIds: list[str]
    usedWebSources: list[AskWebSourceResponse]
    contextAskTurnIds: list[str]
    canWriteback: bool
    citations: list[AskCitationResponse]
    createdAt: datetime
```

Mirror the same additions in `web/lib/types.ts`.

- [ ] **Step 6: Run the focused tests again**

Run: `cd server && python -m pytest tests/test_research_api.py -k ask`
Expected: still FAIL, but now on runtime behavior rather than missing shape definitions.

Run: `cd web && node --import tsx --test tests/research-api.test.tsx`
Expected: PASS, or fail only because the runtime implementation has not yet been upgraded in Tasks 2-6.


### Task 2: Introduce Ask-specific runtime schemas and helper boundaries

**Files:**
- Modify: `server/inkdesk_server/agents.py`
- Modify: `server/inkdesk_server/research.py`
- Test: `server/tests/test_agent_runtime.py`

- [ ] **Step 1: Write failing runtime tests for contextual Ask and web evidence output**

Add tests in `server/tests/test_agent_runtime.py` similar to:

```python
response = runtime.answer(
    AskRequestModel(
        question="请继续细化这里的证据边界",
        mode="vault_plus_web",
        pendingReviewCount=1,
        topic=topic,
        citations=[citation],
        contextTurns=[context_turn],
    )
)
assert response.contextAskTurnIds == ["ask-prev"]
assert isinstance(response.usedWebSources, list)
assert response.canWriteback is True
```

- [ ] **Step 2: Run the focused runtime test to verify red state**

Run: `cd server && python -m pytest tests/test_agent_runtime.py -k ask`
Expected: FAIL because `AskRequestModel` and `AskResponseModel` do not yet support context turns or web evidence.

- [ ] **Step 3: Extend `agents.py` with Ask-specific Pydantic helper models**

Add new models near the existing Ask schemas:

```python
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
    usedWebSources: list[WebCitationModel] = []
```

Then update `AskRequestModel` and `AskResponseModel` to carry:

```python
contextTurns: list[AskContextTurnModel] = []
continueFromAskTurnId: str | None = None
usedWebSources: list[WebCitationModel] = []
contextAskTurnIds: list[str] = []
canWriteback: bool = True
writebackPackage: AskWritebackPackageModel | None = None
```

- [ ] **Step 4: Add JSON encode/decode helpers in `research.py` for AskTurn snapshot fields**

Add helpers such as:

```python
def encode_json_payload(self, value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def decode_json_list(self, raw: str | None) -> list[str]:
    if not raw:
        return []
    return list(json.loads(raw))
```

Keep them scoped to Ask snapshot persistence and avoid broader refactors.

- [ ] **Step 5: Run the runtime tests again**

Run: `cd server && python -m pytest tests/test_agent_runtime.py -k ask`
Expected: FAIL on graph behavior, which is the next task, not on missing model fields.


### Task 3: Refactor Ask runtime into staged LangGraph execution

**Files:**
- Modify: `server/inkdesk_server/agents.py`
- Test: `server/tests/test_agent_runtime.py`

- [ ] **Step 1: Write failing tests for staged Ask behavior**

Add deterministic tests proving:

```python
vault_only = runtime.answer(vault_request)
assert vault_only.usedWebSources == []

vault_plus_web = runtime.answer(vault_plus_web_request)
assert vault_plus_web.knowledgeGaps
assert vault_plus_web.canWriteback is True
```

and a branch test like:

```python
assert state["needs_web_assist"] is False
```

for vault-only runs.

- [ ] **Step 2: Run the Ask runtime suite and verify it fails**

Run: `cd server && python -m pytest tests/test_agent_runtime.py`
Expected: FAIL because the Ask graph still only has `prepare_prompt -> generate_answer`.

- [ ] **Step 3: Replace the thin Ask graph with staged state transitions**

Refactor the Ask graph from:

```python
graph = StateGraph(AskState)
graph.add_node("prepare_prompt", self._prepare_ask_prompt)
graph.add_node("generate_answer", self._generate_ask_answer)
graph.add_edge(START, "prepare_prompt")
graph.add_edge("prepare_prompt", "generate_answer")
graph.add_edge("generate_answer", END)
```

to:

```python
graph = StateGraph(AskState)
graph.add_node("load_request_context", self._load_request_context)
graph.add_node("retrieve_vault_context", self._retrieve_vault_context)
graph.add_node("assess_evidence", self._assess_evidence)
graph.add_node("optional_web_assist", self._optional_web_assist)
graph.add_node("compose_answer", self._compose_answer)
graph.add_node("build_writeback_package", self._build_writeback_package)
graph.add_edge(START, "load_request_context")
graph.add_edge("load_request_context", "retrieve_vault_context")
graph.add_edge("retrieve_vault_context", "assess_evidence")
graph.add_conditional_edges("assess_evidence", self._route_after_assessment, {
    "web": "optional_web_assist",
    "answer": "compose_answer",
})
graph.add_edge("optional_web_assist", "compose_answer")
graph.add_edge("compose_answer", "build_writeback_package")
graph.add_edge("build_writeback_package", END)
```

- [ ] **Step 4: Implement deterministic node behavior before richer LLM behavior**

Add minimal node implementations that make the tests pass without needing live model calls:

```python
def _route_after_assessment(self, state: AskState) -> str:
    if state["mode"] == "vault_plus_web" and state.get("needs_web_assist"):
        return "web"
    return "answer"
```

and make `_optional_web_assist` return `used_web_sources=[]` for deterministic runtime until the dedicated service is wired in.

- [ ] **Step 5: Re-run the runtime suite**

Run: `cd server && python -m pytest tests/test_agent_runtime.py`
Expected: PASS for staged routing and deterministic Ask output.


### Task 4: Add vault retrieval and web assist services to the research backend

**Files:**
- Modify: `server/inkdesk_server/research.py`
- Modify: `server/inkdesk_server/importers.py`
- Modify: `server/tests/test_research_api.py`

- [ ] **Step 1: Write failing API tests for conditional web assist**

Add a new backend test like:

```python
response = client.post(
    "/api/ask",
    json={"question": "补充外部视角", "mode": "vault_plus_web"},
)
payload = response.json()
assert "usedWebSources" in payload
assert "contextAskTurnIds" in payload
```

and assert vault-only mode keeps `usedWebSources == []`.

- [ ] **Step 2: Run the focused research API suite**

Run: `cd server && python -m pytest tests/test_research_api.py -k "ask or writeback"`
Expected: FAIL because the service layer still passes only topic and citations into the runtime.

- [ ] **Step 3: Add retrieval helpers inside `ResearchWorkspaceService`**

Introduce focused helper methods like:

```python
def build_ask_context_turns(self, ask_turn_id: str | None) -> list[AskContextTurnModel]:
    if not ask_turn_id:
        return []
    ask_turn = self.db.scalar(select(AskTurn).where(AskTurn.id == ask_turn_id))
    if not ask_turn:
        return []
    return [AskContextTurnModel(askTurnId=ask_turn.id, question=ask_turn.question, answer=ask_turn.answer)]

def build_topic_citations(self, topic: Topic | None) -> list[Source]:
    if topic is None:
        return []
    return sorted(topic.sources, key=lambda item: item.updated_at, reverse=True)[:4]

def build_global_citations(self, question: str) -> list[Source]:
    lowered = question.lower()
    ranked = [source for source in self._sources() if lowered in source.title.lower() or lowered in source.excerpt.lower()]
    return (ranked or self._sources())[:4]
```

Keep v1 retrieval deterministic:

- topic Ask: linked sources + thread-proximate sources
- global Ask: recent sources + simple title/excerpt text matches

- [ ] **Step 4: Add a minimal web assist boundary reusing existing web importer primitives**

In `server/inkdesk_server/importers.py`, add a helper shaped like:

```python
class WebAssistResult:
    url: str
    title: str
    excerpt: str
    body: str
    reason_used: str
```

and a method stub:

```python
def assist_from_query(self, query: str) -> list[WebAssistResult]:
    return []
```

v1 can remain deterministic-empty until live search is enabled, but the boundary must exist so Ask graph and writeback package can depend on it safely.

- [ ] **Step 5: Rewire `ResearchWorkspaceService.ask()` to supply follow-up context and consume the richer Ask response**

Change the runtime call from:

```python
draft = self.agent_runtime.answer(
    AskRequestModel(
        question=question,
        mode=mode,
        pendingReviewCount=pending_review_count,
        topic=self.to_agent_topic(topic) if topic else None,
        citations=[self.to_agent_citation(source) for source in candidate_citations],
    )
)
```

to:

```python
draft = self.agent_runtime.answer(
    AskRequestModel(
        question=question,
        mode=mode,
        pendingReviewCount=pending_review_count,
        topic=self.to_agent_topic(topic) if topic else None,
        citations=[self.to_agent_citation(source) for source in candidate_citations],
        continueFromAskTurnId=request.continueFromAskTurnId,
        contextTurns=self.build_ask_context_turns(request.continueFromAskTurnId),
    )
)
```

- [ ] **Step 6: Run the backend Ask tests again**

Run: `cd server && python -m pytest tests/test_research_api.py -k ask`
Expected: PASS for the richer Ask response shape, even if `usedWebSources` is currently empty in deterministic mode.


### Task 5: Persist Ask research snapshots and use them for follow-up context

**Files:**
- Modify: `server/inkdesk_server/research.py`
- Modify: `server/inkdesk_server/models.py`
- Test: `server/tests/test_research_api.py`

- [ ] **Step 1: Write failing persistence tests for follow-up inheritance**

Add a test like:

```python
first = client.post("/api/ask", json={"topicId": topic_id, "question": "先总结一下", "mode": "vault"}).json()
second = client.post(
    "/api/ask",
    json={
        "topicId": topic_id,
        "question": "继续展开刚才的知识缺口",
        "mode": "vault",
        "continueFromAskTurnId": first["id"],
    },
).json()
assert second["contextAskTurnIds"] == [first["id"]]
```

- [ ] **Step 2: Run the test to confirm red state**

Run: `cd server && python -m pytest tests/test_research_api.py -k continue`
Expected: FAIL because `AskTurn` persistence does not yet store parent linkage or context ids.

- [ ] **Step 3: Persist AskTurn snapshot fields when saving a new Ask response**

In `ResearchWorkspaceService.ask()`, replace the thin create block:

```python
ask_turn = AskTurn(
    id=self.new_id("ask"),
    workspace=workspace,
    topic=topic,
    question=question,
    answer=draft.answer,
    citation_source_ids=",".join(source.id for source in citations),
    created_at=now,
)
```

with:

```python
ask_turn = AskTurn(
    id=self.new_id("ask"),
    workspace=workspace,
    topic=topic,
    parent_ask_turn_id=request.continueFromAskTurnId,
    mode=mode,
    question=question,
    answer=draft.answer,
    citation_source_ids=",".join(source.id for source in citations),
    used_wiki_ids=",".join(draft.usedWikiIds),
    used_source_ids=",".join(draft.usedSourceIds),
    used_web_sources_json=self.encode_json_payload([item.model_dump() for item in draft.usedWebSources]),
    knowledge_gaps_json=self.encode_json_payload(draft.knowledgeGaps),
    follow_up_questions_json=self.encode_json_payload(draft.followUpQuestions),
    writeback_package_json=self.encode_json_payload(draft.writebackPackage.model_dump() if draft.writebackPackage else {}),
    created_at=now,
)
```

- [ ] **Step 4: Use persisted AskTurn snapshots to rebuild follow-up context**

Implement `build_ask_context_turns()` so it walks parent linkage conservatively:

```python
def build_ask_context_turns(self, ask_turn_id: str | None) -> list[AskContextTurnModel]:
    if not ask_turn_id:
        return []
    ask_turn = self.db.scalar(select(AskTurn).where(AskTurn.id == ask_turn_id))
    if not ask_turn:
        return []
    return [
        AskContextTurnModel(
            askTurnId=ask_turn.id,
            question=ask_turn.question,
            answer=ask_turn.answer,
        )
    ]
```

Keep v1 to one-hop follow-up context; if deeper thread recovery is needed, treat it as a separate follow-up enhancement after this plan lands.

- [ ] **Step 5: Run the focused follow-up tests**

Run: `cd server && python -m pytest tests/test_research_api.py -k "continue or ask"`
Expected: PASS for inherited `contextAskTurnIds` and persisted follow-up state.


### Task 6: Materialize web-backed writeback into raw plus ingest proposal

**Files:**
- Modify: `server/inkdesk_server/research.py`
- Modify: `server/tests/test_research_api.py`
- Modify: `server/inkdesk_server/vault.py`

- [ ] **Step 1: Write failing tests for Ask writeback idempotency and raw materialization**

Add a test shaped like:

```python
ask_turn = client.post("/api/ask", json={"question": "需要外部网页补料", "mode": "vault_plus_web"}).json()
first = client.post(f"/api/ask/{ask_turn['id']}/writeback").json()
second = client.post(f"/api/ask/{ask_turn['id']}/writeback").json()
assert first["id"] == second["id"]
```

and if the response contains web-backed evidence, assert new raw records exist before the proposal is returned.

- [ ] **Step 2: Run the focused writeback suite**

Run: `cd server && python -m pytest tests/test_research_api.py -k writeback`
Expected: FAIL because writeback still recomputes proposal data directly from AskTurn answer and does not materialize raw from a package.

- [ ] **Step 3: Add a helper that consumes the stored writeback package**

Create a narrow helper in `ResearchWorkspaceService`:

```python
def materialize_writeback_sources(self, ask_turn: AskTurn, now: datetime) -> list[Source]:
    package = self.decode_writeback_package(ask_turn.writeback_package_json)
    created_sources: list[Source] = []
    for web_source in package.usedWebSources:
        existing = self.find_source_by_locator_and_hash(web_source.url, self.vault_service.content_hash(web_source.excerpt))
        if existing:
            created_sources.append(existing)
            continue
        imported = ImportedRawMaterial(
            kind="WEB",
            title=web_source.title,
            locator=web_source.url,
            excerpt=web_source.excerpt,
            body=web_source.excerpt,
        )
        created_sources.append(self._create_source_from_material(imported, now))
    return created_sources
```

Extract `_create_source_from_material()` from `create_imported_source()` instead of duplicating source creation logic.

- [ ] **Step 4: Refactor `create_ask_writeback_proposal()` to use persisted package plus materialized raw**

Replace the current direct derivation approach with:

```python
materialized_sources = self.materialize_writeback_sources(ask_turn, now)
package = self.decode_writeback_package(ask_turn.writeback_package_json)
proposal_hash = self.vault_service.content_hash(
    f"ask-writeback|{ask_turn.id}|{package.proposedUnderstanding}|{','.join(source.id for source in materialized_sources)}"
)
```

Then create the `ReviewItem` from package values rather than recomputing title/claim/open question from the raw Ask answer.

- [ ] **Step 5: Run the writeback-focused backend tests**

Run: `cd server && python -m pytest tests/test_research_api.py -k writeback`
Expected: PASS for proposal idempotency and raw-before-ingest materialization behavior.


### Task 7: Update frontend Ask UX for follow-up context and web evidence boundaries

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/research.ts`
- Modify: `web/app/app/ask/page.tsx`
- Modify: `web/tests/research-pages.test.tsx`
- Modify: `web/tests/research-api.test.tsx`
- Modify: `web/tests/e2e/local-fullstack.spec.ts`

- [ ] **Step 1: Write failing frontend tests for follow-up context and web evidence sections**

Add expectations in `web/tests/research-pages.test.tsx` such as:

```tsx
expect(screen.getByText(/正在延续上一轮问答/)).toBeInTheDocument();
expect(screen.getByText(/这些外部资料还没有进入你的 vault/)).toBeInTheDocument();
expect(screen.getByRole("button", { name: /会先保存外部来源到 raw/ })).toBeInTheDocument();
```

- [ ] **Step 2: Run the focused frontend test to verify red state**

Run: `cd web && node --import tsx --test tests/research-pages.test.tsx`
Expected: FAIL because the Ask page does not yet render follow-up context or web evidence disclosures.

- [ ] **Step 3: Extend the frontend request/response types and client**

Update `web/lib/types.ts`:

```ts
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
```

- [ ] **Step 4: Update `web/app/app/ask/page.tsx` to preserve follow-up context**

Thread `continueFromAskTurnId` through query params:

```tsx
type AskPageProps = {
  searchParams: Promise<{
    q?: string;
    topicId?: string;
    mode?: string;
    continueFromAskTurnId?: string;
  }>;
};
```

and update `askHref()` to keep it:

```tsx
function askHref(nextQuestion: string, nextMode = mode, nextTopicId = topicId, nextContinueFromAskTurnId = answer?.id ?? continueFromAskTurnId) {
  const params = new URLSearchParams();
  params.set("q", nextQuestion);
  if (nextTopicId) params.set("topicId", nextTopicId);
  if (nextContinueFromAskTurnId) params.set("continueFromAskTurnId", nextContinueFromAskTurnId);
  params.set("mode", nextMode);
  return `/app/ask?${params.toString()}`;
}
```

- [ ] **Step 5: Render web evidence and writeback boundary messaging**

In the answer card, add UI like:

```tsx
{answer.usedWebSources.length > 0 ? (
  <>
    <div className="mt-6 text-[11px] uppercase tracking-[0.2em] text-ink-muted">本次回答临时使用了外部网页</div>
    <div className="mt-4 rounded-[22px] bg-[#fff5e9] px-4 py-4 text-sm leading-7 text-ink-text">
      这些外部资料还没有进入你的 vault。
    </div>
  </>
) : null}
```

and change the button label conditionally:

```tsx
const writebackLabel =
  answer.usedWebSources.length > 0
    ? "沉淀到 wiki（会先保存外部来源到 raw）"
    : "沉淀到 wiki";
```

- [ ] **Step 6: Re-run focused frontend tests**

Run: `cd web && node --import tsx --test tests/research-pages.test.tsx tests/research-api.test.tsx`
Expected: PASS for Ask page rendering and API shape handling.


### Task 8: Full verification and cleanup

**Files:**
- Verify: `server/tests/*`
- Verify: `web/tests/*`
- Verify: `docs/superpowers/specs/2026-05-02-ask-researcher-design.md`
- Verify: `docs/superpowers/plans/2026-05-02-ask-researcher.md`

- [ ] **Step 1: Run the full backend suite**

Run: `cd server && python -m pytest`
Expected: all tests PASS.

- [ ] **Step 2: Run the frontend smoke and unit suite**

Run: `cd web && npm test`
Expected: PASS.

- [ ] **Step 3: Run typecheck**

Run: `cd web && npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Run lint**

Run: `cd web && npm run lint`
Expected: PASS.

- [ ] **Step 5: Run production build**

Run: `cd web && npm run build`
Expected: PASS.

- [ ] **Step 6: Run E2E**

Run: `cd web && npm run e2e`
Expected: PASS, with `local-fullstack.spec.ts` skipped unless the fullstack flag is set.

- [ ] **Step 7: Review the diff for accidental scope creep**

Check that the implementation does **not** introduce:

- full Ask history pages
- automatic raw import on web assist
- direct wiki edits from Ask
- multi-agent orchestration

- [ ] **Step 8: Commit**

```bash
git add server/inkdesk_server/models.py server/inkdesk_server/schemas.py server/inkdesk_server/agents.py server/inkdesk_server/research.py server/inkdesk_server/importers.py server/tests/test_agent_runtime.py server/tests/test_research_api.py web/lib/types.ts web/lib/research.ts web/app/app/ask/page.tsx web/tests/research-pages.test.tsx web/tests/research-api.test.tsx web/tests/e2e/local-fullstack.spec.ts docs/superpowers/specs/2026-05-02-ask-researcher-design.md docs/superpowers/plans/2026-05-02-ask-researcher.md
git commit -m "feat: add ask researcher runtime and writeback flow"
```
