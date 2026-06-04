# Ask-to-Deposit Main Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `omni-superdev` first, then use `superpowers:test-driven-development` for behavior changes and `webapp-testing` for local UI verification. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Ask -> 沉淀` the primary Inkdesk product path before building Skill Workbench, Wiki Health, Evaluation Harness, or external Agent connectors.

**Architecture:** Reuse the existing `AskTurn -> writeback -> ReviewItem -> ingest -> wiki` path instead of creating a parallel deposit system. Introduce a clearer `deposit` contract over the current writeback internals, add answer-level and selection-level deposit inputs, keep all canonical wiki mutations behind review, and record enough metadata for later Skill Workbench, evaluation, and external Agent deposit.

**Tech Stack:** Next.js 16, React 19, TypeScript, FastAPI, SQLAlchemy, LangGraph, PostgreSQL, Vault Markdown, pytest, Vitest, node:test, Playwright

---

## Product Decision

The next development slice is not Skill Workbench yet.

The article's `Claude Code + Skill repo + Obsidian` shape is useful, but Inkdesk should first make the memory entry point stable. If `Ask -> 沉淀` is weak, Skill Workbench and external Agent deposit will only add more surfaces on top of an unclear write path.

Current implementation already has:

- `AskTurn` snapshots in `server/inkdesk_server/models.py`.
- Ask writeback through `POST /api/ask/{ask_turn_id}/writeback`.
- Review proposals through `ReviewItem`.
- Vault-first accepted wiki writes.
- Frontend `AskAnswerCard` with a writeback button.

Next target:

```text
Ask answer -> deposit request -> review proposal -> owner accepts -> wiki patch
```

with two user-facing entry points:

- Deposit whole answer.
- Deposit selected excerpt.

## Delivery Order

1. Stabilize backend deposit contract over existing writeback.
2. Add answer-level deposit feedback and idempotency.
3. Add selected-excerpt deposit.
4. Upgrade Ask UI into an explicit deposit surface.
5. Add health/readiness signals for pending deposits.
6. Update docs and then move to Skill Workbench.

## Planned File Map

- Modify: `server/inkdesk_server/schemas.py`
  - Add request/response contracts for Ask deposit.
- Modify: `server/inkdesk_server/main.py`
  - Add deposit endpoint aliases while keeping existing writeback endpoint compatible.
- Modify: `server/inkdesk_server/research.py`
  - Reuse `create_ask_writeback_proposal()` as the implementation base, then split into clearer deposit helpers.
- Modify: `server/inkdesk_server/models.py`
  - Only add columns if required for selected-excerpt metadata; avoid migration unless tests prove current payload cannot carry it.
- Modify: `server/tests/test_research_api.py`
  - Cover whole-answer deposit, selected-excerpt deposit, idempotency, and review safety.
- Modify: `web/lib/types.ts`
  - Add frontend deposit request/response types.
- Modify: `web/lib/research.ts`
  - Add `depositAskAnswer()` and `depositAskSelection()` wrappers.
- Modify: `web/components/workbench/ask-answer-card.tsx`
  - Make deposit a fixed answer action with clear states.
- Modify: `web/components/workbench/ask-workspace.tsx`
  - Wire server actions and redirect/feedback behavior.
- Modify: `web/tests/research-pages.test.tsx`
  - Assert the Ask page exposes the new deposit surface.
- Modify: `web/tests/research-api.test.tsx`
  - Assert frontend API wrappers call the correct endpoints.
- Modify: `docs/product/product-roadmap.md`
  - Mark this plan as the active next slice.

## Task 1: Define The Deposit Contract

**Files:**

- Modify: `server/inkdesk_server/schemas.py`
- Modify: `server/inkdesk_server/main.py`
- Modify: `server/tests/test_research_api.py`

- [ ] **Step 1: Add failing backend API tests for whole-answer deposit**

Add a test in `server/tests/test_research_api.py` that creates an Ask turn, calls the new endpoint, and verifies the result remains a review proposal:

```python
def test_deposit_whole_ask_answer_creates_review_proposal(temp_app_env):
    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]
    ask_turn = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "这条回答应该如何沉淀？", "mode": "vault"},
    ).json()

    response = client.post(f"/api/ask/{ask_turn['id']}/deposit", json={"mode": "answer"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "TOPIC_PATCH"
    assert payload["targetTopicId"] == topic_id
    assert payload["proposalPayload"]["topicDecision"]["decision"] == "PATCH"
```

- [ ] **Step 2: Run the focused backend test and verify it fails**

Run:

```powershell
cd server
python -m pytest tests/test_research_api.py -k deposit
```

Expected: FAIL because `/api/ask/{id}/deposit` does not exist.

- [ ] **Step 3: Add request schema**

Add to `server/inkdesk_server/schemas.py`:

```python
class AskDepositRequest(BaseModel):
    mode: Literal["answer", "selection"] = "answer"
    selectedText: str | None = None
    reason: str | None = None
```

Use `typing.Literal`; if the file already imports `Literal`, reuse the import.

- [ ] **Step 4: Add endpoint alias**

Add to `server/inkdesk_server/main.py`:

```python
@app.post("/api/ask/{ask_turn_id}/deposit", response_model=ReviewItemResponse)
def ask_deposit(
    ask_turn_id: str,
    request: AskDepositRequest,
    _: Annotated[VerifiedOwnerSession, Depends(require_owner)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    return get_research_service(db, settings).create_ask_deposit_proposal(ask_turn_id, request)
```

Keep `/api/ask/{ask_turn_id}/writeback` for compatibility.

- [ ] **Step 5: Implement `create_ask_deposit_proposal()` as a thin wrapper**

Add to `server/inkdesk_server/research.py`:

```python
def create_ask_deposit_proposal(self, ask_turn_id: str, request: AskDepositRequest) -> ReviewItemResponse:
    if request.mode == "selection":
        return self.create_ask_selection_deposit_proposal(ask_turn_id, request)
    return self.create_ask_writeback_proposal(ask_turn_id)
```

At this task, `selection` can raise a controlled validation error until Task 3.

- [ ] **Step 6: Run backend tests**

Run:

```powershell
cd server
python -m pytest tests/test_research_api.py -k "deposit or writeback"
```

Expected: PASS for whole-answer deposit and existing writeback tests.

## Task 2: Make Deposit Idempotency And Feedback Explicit

**Files:**

- Modify: `server/inkdesk_server/research.py`
- Modify: `server/tests/test_research_api.py`
- Modify: `web/lib/types.ts`
- Modify: `web/lib/research.ts`
- Modify: `web/tests/research-api.test.tsx`

- [ ] **Step 1: Add failing idempotency test**

Add:

```python
def test_deposit_whole_ask_answer_is_idempotent(temp_app_env):
    client = owner_client(temp_app_env)
    ask_turn = client.post("/api/ask", json={"question": "沉淀同一条回答", "mode": "vault"}).json()

    first = client.post(f"/api/ask/{ask_turn['id']}/deposit", json={"mode": "answer"}).json()
    second = client.post(f"/api/ask/{ask_turn['id']}/deposit", json={"mode": "answer"}).json()

    assert first["id"] == second["id"]
```

- [ ] **Step 2: Run focused test**

Run:

```powershell
cd server
python -m pytest tests/test_research_api.py -k deposit
```

Expected: If it already passes through existing `content_hash`, keep the current implementation. If it fails, fix only the hash derivation.

- [ ] **Step 3: Add frontend API wrapper**

Add to `web/lib/types.ts`:

```ts
export type ResearchAskDepositRequest = {
  mode: "answer" | "selection";
  selectedText?: string;
  reason?: string;
};
```

Add to `web/lib/research.ts`:

```ts
export async function depositAskAnswer(askTurnId: string, ownerSession?: string): Promise<ResearchReviewItem> {
  return withResearchFallback(
    () => postInkdeskJson<ResearchReviewItem>(`/ask/${askTurnId}/deposit`, { mode: "answer" }, { ownerSession }),
    () => createAskWritebackFixture(askTurnId)
  );
}
```

- [ ] **Step 4: Add frontend API test**

In `web/tests/research-api.test.tsx`, assert `depositAskAnswer("ask-001")` posts to `/api/ask/ask-001/deposit`.

- [ ] **Step 5: Run frontend API tests**

Run:

```powershell
cd web
node --import tsx --test tests/research-api.test.tsx
```

Expected: PASS.

## Task 3: Add Selected-Excerpt Deposit

**Files:**

- Modify: `server/inkdesk_server/research.py`
- Modify: `server/tests/test_research_api.py`
- Modify: `web/lib/types.ts`
- Modify: `web/lib/research.ts`
- Modify: `web/tests/research-api.test.tsx`

- [ ] **Step 1: Add failing backend test for selected text**

Add:

```python
def test_deposit_selected_ask_excerpt_uses_selected_text(temp_app_env):
    client = owner_client(temp_app_env)
    ask_turn = client.post("/api/ask", json={"question": "请给出可以沉淀的判断", "mode": "vault"}).json()

    response = client.post(
        f"/api/ask/{ask_turn['id']}/deposit",
        json={
            "mode": "selection",
            "selectedText": "只沉淀这一句稳定判断。",
            "reason": "这是用户选中的长期结论。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "只沉淀这一句稳定判断" in payload["proposedUnderstanding"]
    assert payload["proposalPayload"]["explanation"]
```

- [ ] **Step 2: Run focused backend test**

Run:

```powershell
cd server
python -m pytest tests/test_research_api.py -k selected
```

Expected: FAIL until selection mode is implemented.

- [ ] **Step 3: Implement selection proposal creation**

In `server/inkdesk_server/research.py`, implement `create_ask_selection_deposit_proposal()` by reusing the same topic routing and evidence source resolution as `create_ask_writeback_proposal()`, but override:

```python
proposal_understanding = request.selectedText.strip()
proposal_claim = self.first_sentence(request.selectedText.strip())
proposal_open_question = request.reason.strip() if request.reason else self.derive_ask_writeback_open_question(ask_turn)
```

Guardrails:

- Reject empty `selectedText`.
- Reject text longer than the original answer if it is not contained in `ask_turn.answer`.
- Do not write wiki directly.
- Use `content_hash` that includes `ask_turn.id`, selected text, target vault path, and materialized source ids.

- [ ] **Step 4: Add frontend wrapper**

Add to `web/lib/research.ts`:

```ts
export async function depositAskSelection(
  askTurnId: string,
  request: Omit<ResearchAskDepositRequest, "mode">,
  ownerSession?: string
): Promise<ResearchReviewItem> {
  return postInkdeskJson<ResearchReviewItem>(
    `/ask/${askTurnId}/deposit`,
    { mode: "selection", ...request },
    { ownerSession }
  );
}
```

- [ ] **Step 5: Run focused backend and frontend tests**

Run:

```powershell
cd server
python -m pytest tests/test_research_api.py -k "deposit or selected or writeback"
```

Run:

```powershell
cd web
node --import tsx --test tests/research-api.test.tsx
```

Expected: PASS.

## Task 4: Upgrade Ask UI Into A Deposit Surface

**Files:**

- Modify: `web/components/workbench/ask-answer-card.tsx`
- Modify: `web/components/workbench/ask-workspace.tsx`
- Modify: `web/tests/research-pages.test.tsx`
- Modify: `web/tests/unit/workbench-components.test.tsx`

- [ ] **Step 1: Add failing page assertions**

Update `web/tests/research-pages.test.tsx` to assert:

```ts
assert.match(askHtml, /沉淀这次回答/);
assert.match(askHtml, /选中片段后也可以沉淀/);
assert.match(askHtml, /只会进入 ingest 审阅/);
```

- [ ] **Step 2: Run page tests**

Run:

```powershell
cd web
node --import tsx --test tests/research-pages.test.tsx
```

Expected: FAIL until UI copy/actions are updated.

- [ ] **Step 3: Rename visible action**

In `web/components/workbench/ask-answer-card.tsx`, change the primary button label from `沉淀到 wiki` to:

```text
沉淀这次回答
```

Keep the safety copy:

```text
只会进入 ingest 审阅，不会直接改写 wiki。
```

- [ ] **Step 4: Add selected-excerpt form**

Add a compact form under the answer body:

```tsx
<textarea
  className="min-h-24 w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm leading-7 text-ink-text"
  name="selectedText"
  placeholder="可选：粘贴你想单独沉淀的片段"
/>
<input name="askTurnId" type="hidden" value={answer.id} />
<button className="rounded-full bg-ink-primarySoft px-5 py-3 text-sm font-semibold text-ink-primary" type="submit">
  沉淀选中片段
</button>
```

Use a separate server action in `ask-workspace.tsx` that calls `depositAskSelection()`.

- [ ] **Step 5: Preserve current redirect behavior**

After deposit succeeds:

```ts
redirect(`/app/ingest?created=${review.id}`);
```

This keeps review-first behavior explicit.

- [ ] **Step 6: Run frontend tests**

Run:

```powershell
cd web
npm test
npm run typecheck
```

Expected: PASS.

## Task 5: Add Deposit Readiness Signals

**Files:**

- Modify: `server/inkdesk_server/research.py`
- Modify: `server/tests/test_research_api.py`
- Modify: `web/components/workbench/ask-answer-card.tsx`
- Modify: `web/tests/research-pages.test.tsx`

- [ ] **Step 1: Add backend expectations for non-depositable answers**

Extend tests around `canWriteback` so the frontend can rely on:

```python
assert isinstance(payload["canWriteback"], bool)
```

If deterministic runtime currently always returns `True`, keep that behavior for now. Do not invent complex scoring in this slice.

- [ ] **Step 2: Make UI states explicit**

In `AskAnswerCard`, show:

- `可沉淀` when `answer.canWriteback` is true.
- `暂不适合沉淀` when false.
- `需要补证` when `answer.knowledgeGaps.length > 0`.

- [ ] **Step 3: Ensure pending deposit no longer appears as fresh writeback candidate**

Run existing tests:

```powershell
cd server
python -m pytest tests/test_research_api.py -k "writebackCandidate or deposit"
```

Expected: PASS. Existing pending-review de-duplication should still work.

## Task 6: Verification, Documentation, And Handoff

**Files:**

- Modify: `docs/product/product-roadmap.md`
- Modify: `README.md` only if product entry wording changes

- [ ] **Step 1: Run backend suite**

Run:

```powershell
cd server
python -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend suite**

Run:

```powershell
cd web
npm test
npm run typecheck
npm run lint
```

Expected: all checks pass.

- [ ] **Step 3: Run build**

Run:

```powershell
cd web
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Run local UI verification if fullstack services are available**

Run:

```powershell
cd web
npm run e2e
```

Expected: Playwright passes or reports the documented fullstack prerequisite.

- [ ] **Step 5: Update roadmap status**

In `docs/product/product-roadmap.md`, mark:

- Whole-answer deposit complete.
- Selected-excerpt deposit complete.
- Deposit still review-first.
- Skill Workbench remains next, not current.

- [ ] **Step 6: Commit in small slices**

Recommended commit sequence:

```bash
git commit -m "feat: add ask deposit endpoint"
git commit -m "feat: support selected ask deposit"
git commit -m "feat: make ask deposit the primary action"
git commit -m "docs: update ask deposit roadmap"
```

## Acceptance Criteria

- Every Ask answer has a fixed `沉淀这次回答` action when `canWriteback` is true.
- The user can deposit a whole answer.
- The user can deposit selected text from an answer.
- Both deposit paths create `ReviewItem` proposals and do not directly edit wiki files.
- Repeating the same deposit does not create duplicate pending proposals.
- External web evidence, if present, is materialized through raw before review.
- Existing `/api/ask/{id}/writeback` remains compatible.
- `/app/ingest` remains the review gate.
- Backend and frontend verification commands pass.

## Out Of Scope For This Slice

- Building Skill Workbench UI.
- Creating `vault/schema/` and `vault/skills/` directories.
- Adding MCP server or CLI.
- Adding multi-agent deposit orchestration.
- Adding statistical evaluation harness.
- Letting AI automatically accept wiki changes.

## Next Slice After Completion

After this plan lands, start:

```text
Vault schema/skills conventions -> Skill file model -> Skill Workbench list/detail -> skill run records
```

That next slice should treat deposit as the shared output path for skills, external Agent work, and future evaluation traces.
