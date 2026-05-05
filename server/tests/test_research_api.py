from __future__ import annotations

from base64 import b64decode
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select


SAMPLE_PDF = b64decode(
    "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWyA0IDAgUiBdCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Ci9Gb250IDw8Ci9GMSA1IDAgUgo+Pgo+PgovTWVkaWFCb3ggWyAwLjAgMC4wIDMwMCAxNDQgXQovUGFyZW50IDIgMCBSCi9Db250ZW50cyA2IDAgUgo+PgplbmRvYmoKNSAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0xlbmd0aCA1Ngo+PgpzdHJlYW0KQlQKL0YxIDE4IFRmCjM2IDk2IFRkCihUb3BpYyBtZW1vcnkgbmVlZHMgcmV2aWV3LikgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDA1NCAwMDAwMCBuIAowMDAwMDAwMTEzIDAwMDAwIG4gCjAwMDAwMDAxNjIgMDAwMDAgbiAKMDAwMDAwMDI5NCAwMDAwMCBuIAowMDAwMDAwMzY0IDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNwovUm9vdCAzIDAgUgovSW5mbyAxIDAgUgo+PgpzdGFydHhyZWYKNDcwCiUlRU9GCg=="
)


def owner_client(temp_app_env: Path) -> TestClient:
    from inkvault_server.main import create_app

    client = TestClient(create_app())
    client.cookies.set("inkvault_owner_session", "owner")
    return client


def test_dashboard_bootstraps_legacy_notes_into_raw_and_pending_ingest(temp_app_env):
    client = owner_client(temp_app_env)

    response = client.get("/api/admin/home")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["activeTopics"] == 0
    assert payload["summary"]["pendingReviews"] == 3
    assert payload["summary"]["inboxSources"] == 3
    assert payload["summary"]["totalSources"] == 3
    assert payload["recentSources"][0]["kind"] == "LEGACY_NOTE"
    assert payload["pendingReviews"][0]["kind"] == "TOPIC_CREATE"
    assert payload["pendingReviews"][0]["proposalPayload"]["topicDecision"]["decision"] == "CREATE"
    assert (temp_app_env / "raw").is_dir()
    assert (temp_app_env / "wiki").is_dir()
    assert (temp_app_env / "AGENTS.md").exists()


def test_raw_import_and_wiki_accept_flow(temp_app_env):
    client = owner_client(temp_app_env)

    create_response = client.post(
        "/api/raw",
        json={
            "kind": "WEB",
            "title": "将 Inkvault 重定位为私有研究型 LLM Wiki：外部评注",
            "locator": "https://example.com/research-wiki",
            "excerpt": "来自网页的新证据，强调研究型知识编译而不是传统笔记。",
            "body": "网页正文：研究系统应先做主题编译，再做长期记忆。",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["kind"] == "WEB"

    ingest_list = client.get("/api/ingest")
    assert ingest_list.status_code == 200
    review_id = ingest_list.json()[0]["id"]

    accept_response = client.post(f"/api/ingest/{review_id}/accept")
    assert accept_response.status_code == 200
    topic_id = accept_response.json()["topicId"]

    wiki_response = client.get(f"/api/wiki/{topic_id}")
    assert wiki_response.status_code == 200
    wiki_payload = wiki_response.json()
    assert len(wiki_payload["sources"]) >= 1
    assert len(wiki_payload["keyClaims"]) >= 1
    assert wiki_payload["vaultPath"].startswith("wiki/")
    markdown = (temp_app_env / wiki_payload["vaultPath"]).read_text(encoding="utf-8")
    assert "## Current Understanding" in markdown
    assert "## Sources" in markdown


def test_pdf_import_endpoint_accepts_extractable_pdf(temp_app_env):
    client = owner_client(temp_app_env)

    response = client.post(
        "/api/raw/pdf",
        files={"file": ("topic-memory.pdf", SAMPLE_PDF, "application/pdf")},
        data={"title": "Topic memory PDF"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["kind"] == "PDF"
    assert payload["vaultPath"].startswith("raw/")


def test_topic_scoped_and_global_ask_return_grounded_answers(temp_app_env):
    client = owner_client(temp_app_env)

    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    topic_response = client.post(
        "/api/ask",
        json={
            "topicId": topic_id,
            "question": "这个主题当前最重要的理解是什么？",
            "mode": "vault",
        },
    )
    assert topic_response.status_code == 200
    topic_payload = topic_response.json()
    assert topic_payload["topicId"] == topic_id
    assert topic_payload["parentAskTurnId"] is None
    assert topic_payload["threadRootAskTurnId"] == topic_payload["id"]
    assert topic_payload["lineageAskTurnIds"] == [topic_payload["id"]]
    assert topic_payload["retrievalMode"] == "lexical_fallback"
    assert topic_payload["usedChunkIds"]
    assert topic_payload["usedWikiIds"] == [topic_id]
    assert len(topic_payload["citations"]) == 1
    assert topic_payload["citations"][0]["entityType"] == "TOPIC"
    assert topic_payload["citations"][0]["entityId"] == topic_id
    assert topic_payload["citations"][0]["chunkId"] in topic_payload["usedChunkIds"]
    assert topic_payload["citations"][0]["snippet"]
    assert topic_payload["contextAskTurnIds"] == []
    assert topic_payload["canWriteback"] is True
    assert topic_payload["usedWebSources"] == []

    continued_response = client.post(
        "/api/ask",
        json={
            "topicId": topic_id,
            "question": "延续上一轮，哪些点还需要联网核实？",
            "mode": "vault_plus_web",
            "continueFromAskTurnId": topic_payload["id"],
        },
    )
    assert continued_response.status_code == 200
    continued_payload = continued_response.json()
    assert continued_payload["topicId"] == topic_id
    assert continued_payload["parentAskTurnId"] == topic_payload["id"]
    assert continued_payload["threadRootAskTurnId"] == topic_payload["id"]
    assert continued_payload["lineageAskTurnIds"] == [topic_payload["id"], continued_payload["id"]]
    assert continued_payload["retrievalMode"] == "lexical_fallback"
    assert continued_payload["usedChunkIds"]
    assert continued_payload["contextAskTurnIds"] == [topic_payload["id"]]
    assert continued_payload["canWriteback"] is True
    assert continued_payload["usedWebSources"] == []

    global_response = client.post(
        "/api/ask",
        json={"question": "现在有哪些待审阅的研究迁移项？", "mode": "vault_plus_web"},
    )
    assert global_response.status_code == 200
    global_payload = global_response.json()
    assert global_payload["topicId"] is None
    assert global_payload["parentAskTurnId"] is None
    assert global_payload["threadRootAskTurnId"] == global_payload["id"]
    assert global_payload["lineageAskTurnIds"] == [global_payload["id"]]
    assert global_payload["retrievalMode"] == "lexical_fallback"
    assert global_payload["usedChunkIds"]
    assert len(global_payload["knowledgeGaps"]) == 1
    assert len(global_payload["citations"]) >= 2
    assert all(citation["chunkId"] in global_payload["usedChunkIds"] for citation in global_payload["citations"])
    assert global_payload["contextAskTurnIds"] == []
    assert global_payload["canWriteback"] is True
    assert global_payload["usedWebSources"] == []

    ask_detail = client.get(f"/api/ask/{continued_payload['id']}")
    assert ask_detail.status_code == 200
    detail_payload = ask_detail.json()
    assert detail_payload["id"] == continued_payload["id"]
    assert detail_payload["parentAskTurnId"] == topic_payload["id"]
    assert detail_payload["threadRootAskTurnId"] == topic_payload["id"]
    assert detail_payload["lineageAskTurnIds"] == [topic_payload["id"], continued_payload["id"]]

    thread_response = client.get(f"/api/ask/{continued_payload['id']}/thread")
    assert thread_response.status_code == 200
    thread_payload = thread_response.json()
    assert thread_payload["rootAskTurnId"] == topic_payload["id"]
    assert thread_payload["currentAskTurnId"] == continued_payload["id"]
    assert thread_payload["topicId"] == topic_id
    assert [turn["id"] for turn in thread_payload["turns"]] == [topic_payload["id"], continued_payload["id"]]


def test_explicit_ask_writeback_creates_review_instead_of_silent_wiki_edit(temp_app_env):
    client = owner_client(temp_app_env)

    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]
    ask_turn = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "这个回答值得沉淀到 wiki 吗？", "mode": "vault"},
    ).json()

    response = client.post(f"/api/ask/{ask_turn['id']}/writeback")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "TOPIC_PATCH"
    assert payload["targetTopicId"] == topic_id
    assert payload["proposalPayload"]["topicDecision"]["decision"] == "PATCH"


def test_follow_up_ask_rejects_cross_topic_context(temp_app_env):
    client = owner_client(temp_app_env)

    initial_reviews = client.get("/api/ingest").json()
    first_topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]
    second_topic_id = client.post(f"/api/ingest/{initial_reviews[1]['id']}/accept").json()["topicId"]
    first_topic_ask = client.post(
        "/api/ask",
        json={"topicId": first_topic_id, "question": "先总结这个主题", "mode": "vault"},
    ).json()

    response = client.post(
        "/api/ask",
        json={
            "topicId": second_topic_id,
            "question": "延续上一轮继续追问",
            "mode": "vault",
            "continueFromAskTurnId": first_topic_ask["id"],
        },
    )

    assert response.status_code == 404

    topic_to_global_response = client.post(
        "/api/ask",
        json={
            "question": "把主题问答拿到全局继续追问",
            "mode": "vault",
            "continueFromAskTurnId": first_topic_ask["id"],
        },
    )

    assert topic_to_global_response.status_code == 404

    global_ask = client.post(
        "/api/ask",
        json={"question": "先全局看看现在的研究状态", "mode": "vault"},
    ).json()

    global_to_topic_response = client.post(
        "/api/ask",
        json={
            "topicId": first_topic_id,
            "question": "把全局问答切回某个 topic 继续追问",
            "mode": "vault",
            "continueFromAskTurnId": global_ask["id"],
        },
    )

    assert global_to_topic_response.status_code == 404


def test_global_ask_prioritizes_text_matched_sources_over_recency(temp_app_env):
    client = owner_client(temp_app_env)

    matched_source = client.post(
        "/api/raw",
        json={
            "kind": "TEXT",
            "title": "量子检索边界备忘",
            "excerpt": "这份旧来源讨论量子检索的边界和证据不足问题。",
            "body": "量子检索边界需要更多外部证据来确认。",
        },
    ).json()
    client.post(
        "/api/raw",
        json={
            "kind": "TEXT",
            "title": "最近导入但不相关的来源 A",
            "excerpt": "这是更新但不匹配提问的来源。",
            "body": "与量子检索无关。",
        },
    )
    client.post(
        "/api/raw",
        json={
            "kind": "TEXT",
            "title": "最近导入但不相关的来源 B",
            "excerpt": "这是另一个更新但不匹配提问的来源。",
            "body": "与量子检索无关。",
        },
    )

    response = client.post(
        "/api/ask",
        json={"question": "量子检索现在还缺什么证据？", "mode": "vault_plus_web"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(citation["sourceId"] == matched_source["id"] for citation in payload["citations"])


def test_compile_routes_similar_raw_to_existing_topic_via_chunk_retrieval(temp_app_env):
    client = owner_client(temp_app_env)

    initial_reviews = client.get("/api/ingest").json()
    existing_topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    created_source = client.post(
        "/api/raw",
        json={
            "kind": "TEXT",
            "title": "外部策略补料 001",
            "excerpt": "新的材料强调产品应该聚焦 raw、ingest、wiki 的研究闭环，而不是继续做个人操作系统或公开发布站。",
            "body": "这份补料进一步说明，系统的核心工作是导入网页、PDF 与旧笔记，把材料先保存为 raw，再通过 ingest 转成可审阅的 wiki 记忆。",
        },
    ).json()

    ingest_items = client.get("/api/ingest").json()
    new_review = next(item for item in ingest_items if item["sourceId"] == created_source["id"])

    assert new_review["kind"] == "TOPIC_PATCH"
    assert new_review["targetTopicId"] == existing_topic_id
    assert new_review["proposalPayload"]["topicDecision"]["decision"] == "PATCH"


def test_compile_review_persists_structured_agent_payload_with_chunk_backlinks(temp_app_env):
    from inkvault_server.agents import CompileClaimModel, CompileResponseModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.research import get_research_service

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId

        def fake_compile(request):
            topic_citation_id = next(citation.id for citation in request.citations if citation.kind == "TOPIC")
            return CompileResponseModel(
                kind="TOPIC_PATCH",
                title="把 raw 编译进现有 wiki",
                summary="把补充材料编译进现有 wiki。",
                proposedTopicTitle=None,
                proposedUnderstanding="补充材料强化了 raw / ingest / wiki 的研究闭环。",
                proposedOpenQuestions="还缺少哪条外部对照来源？",
                proposedClaim="新的 raw 材料支持现有 wiki 主题。",
                summaryChanges=["补充材料强化了 raw / ingest / wiki 的研究闭环。"],
                claims=[
                    CompileClaimModel(
                        statement="新的 raw 材料支持现有 wiki 主题。",
                        citationIds=[topic_citation_id],
                    )
                ],
                conflicts=["旧的个人操作系统叙事需要继续降权。"],
                openQuestions=["还缺少哪条外部对照来源？"],
                evidenceCitationIds=[topic_citation_id],
                explanation="因为检索到的 wiki chunk 与新 raw 材料高度一致，所以更适合走 PATCH。",
            )

        service.agent_runtime.compile = fake_compile
        created = service.create_source(
            "TEXT",
            "外部策略补料 003",
            None,
            "新的材料强调产品应该聚焦 raw、ingest、wiki 的研究闭环。",
            "补料进一步说明，系统的核心工作是导入网页、PDF 与旧笔记，再通过 ingest 转成可审阅的 wiki 记忆。",
        )

        review = next(item for item in service.get_review_items() if item.sourceId == created.id)

        assert review.targetTopicId == topic_id
        assert review.proposalPayload.topicDecision.decision == "PATCH"
        assert review.proposalPayload.summaryChanges == ["补充材料强化了 raw / ingest / wiki 的研究闭环。"]
        assert review.proposalPayload.claims[0].statement == "新的 raw 材料支持现有 wiki 主题。"
        assert review.proposalPayload.claims[0].citationChunkIds
        assert review.proposalPayload.conflicts == ["旧的个人操作系统叙事需要继续降权。"]
        assert review.proposalPayload.openQuestions == ["还缺少哪条外部对照来源？"]
        assert review.proposalPayload.explanation == "因为检索到的 wiki chunk 与新 raw 材料高度一致，所以更适合走 PATCH。"
        assert review.proposalPayload.evidence[0].chunkId
        assert review.proposalPayload.evidence[0].entityType == "TOPIC"


def test_accept_review_applies_all_structured_claims_and_open_questions_to_topic(temp_app_env):
    from inkvault_server.agents import CompileClaimModel, CompileResponseModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.research import get_research_service

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId

        def fake_compile(request):
            topic_citation_id = next(citation.id for citation in request.citations if citation.kind == "TOPIC")
            return CompileResponseModel(
                kind="TOPIC_PATCH",
                title="把 raw 编译进现有 wiki",
                summary="把补充材料编译进现有 wiki。",
                proposedTopicTitle=None,
                proposedUnderstanding="补充材料强化了 raw / ingest / wiki 的研究闭环。",
                proposedOpenQuestions="还缺少哪条外部对照来源？",
                proposedClaim="新的 raw 材料支持现有 wiki 主题。",
                summaryChanges=[
                    "补充材料强化了 raw / ingest / wiki 的研究闭环。",
                    "产品主路径需要继续压缩到 research-first workflow。",
                ],
                claims=[
                    CompileClaimModel(
                        statement="新的 raw 材料支持现有 wiki 主题。",
                        citationIds=[topic_citation_id],
                    ),
                    CompileClaimModel(
                        statement="产品主路径需要继续压缩到 research-first workflow。",
                        citationIds=[topic_citation_id],
                    ),
                ],
                conflicts=["旧的个人操作系统叙事需要继续降权。"],
                openQuestions=["还缺少哪条外部对照来源？", "是否需要补一条迁移说明？"],
                evidenceCitationIds=[topic_citation_id],
                explanation="因为检索到的 wiki chunk 与新 raw 材料高度一致，所以更适合走 PATCH。",
            )

        service.agent_runtime.compile = fake_compile
        created = service.create_source(
            "TEXT",
            "外部策略补料 004",
            None,
            "新的材料强调产品应该聚焦 raw、ingest、wiki 的研究闭环。",
            "补料进一步说明，系统的核心工作是导入网页、PDF 与旧笔记，再通过 ingest 转成可审阅的 wiki 记忆。",
        )
        review = next(item for item in service.get_review_items() if item.sourceId == created.id)

        service.accept_review(review.id)
        topic = service.get_topic(topic_id)

        claim_statements = [claim.statement for claim in topic.keyClaims]
        assert "新的 raw 材料支持现有 wiki 主题。" in claim_statements
        assert "产品主路径需要继续压缩到 research-first workflow。" in claim_statements
        assert "还缺少哪条外部对照来源？" in topic.openQuestions
        assert "是否需要补一条迁移说明？" in topic.openQuestions


def test_accept_topic_create_review_applies_structured_payload_to_new_topic(temp_app_env):
    from inkvault_server.agents import CompileClaimModel, CompileResponseModel
    from inkvault_server.core.config import get_settings
    from inkvault_server.db import init_db, session_scope
    from inkvault_server.research import get_research_service

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())

        def fake_compile(_request):
            return CompileResponseModel(
                kind="TOPIC_CREATE",
                title="把 raw 编译成新 wiki",
                summary="基于新 raw 建立新 wiki。",
                proposedTopicTitle="Agent-native 研究记忆系统",
                proposedUnderstanding="系统应该以 Ask 为主入口、以 Compile 为沉淀底座。",
                proposedOpenQuestions="首个版本是否需要默认联网补证？",
                proposedClaim="研究记忆系统需要保留人工审阅环节。",
                summaryChanges=[
                    "系统应该以 Ask 为主入口、以 Compile 为沉淀底座。",
                    "canonical knowledge 只能通过 review 进入 wiki。",
                ],
                claims=[
                    CompileClaimModel(
                        statement="研究记忆系统需要保留人工审阅环节。",
                        citationIds=[],
                    ),
                    CompileClaimModel(
                        statement="Ask 的高质量回答应该可以转成可审阅提案。",
                        citationIds=[],
                    ),
                ],
                conflicts=["旧的 note-first 叙事仍有残留。"],
                openQuestions=["首个版本是否需要默认联网补证？", "是否保留更细粒度 claim 级 accept？"],
                evidenceCitationIds=[],
                explanation="新 raw 还没有足够相似的现有 wiki，因此更适合 CREATE。",
            )

        service.agent_runtime.compile = fake_compile
        created = service.create_source(
            "TEXT",
            "Agent-native 研究记忆补料",
            None,
            "新的材料强调 Ask 与 Compile 应该构成双核心。",
            "补料进一步说明 canonical knowledge 必须经过 review 才能进入 wiki。",
        )
        review = next(item for item in service.get_review_items() if item.sourceId == created.id)

        decision = service.accept_review(review.id)
        topic = service.get_topic(decision.topicId)

        assert topic.title == "Agent-native 研究记忆系统"
        assert "系统应该以 Ask 为主入口、以 Compile 为沉淀底座。" in topic.currentUnderstanding
        assert "canonical knowledge 只能通过 review 进入 wiki。" in topic.currentUnderstanding
        claim_statements = [claim.statement for claim in topic.keyClaims]
        assert "研究记忆系统需要保留人工审阅环节。" in claim_statements
        assert "Ask 的高质量回答应该可以转成可审阅提案。" in claim_statements
        assert "首个版本是否需要默认联网补证？" in topic.openQuestions
        assert "是否保留更细粒度 claim 级 accept？" in topic.openQuestions


def test_vault_plus_web_ask_surfaces_external_web_assist_results_but_keeps_writeback_explicit(temp_app_env, monkeypatch):
    from inkvault_server.importers import WebAssistResult, WebRawImportService
    from inkvault_server.core.config import get_settings

    def fake_assist(_self, query: str):
        assert query == "这个主题的最新变化是什么？"
        return [
            WebAssistResult(
                url="https://example.com/new-evidence",
                title="New Evidence",
                excerpt="这条外部网页补足了最新变化的时间线证据。",
                body="这条外部网页补足了最新变化的时间线证据。",
                reason_used="它补足了 vault 当前缺失的外部时间线来源。",
            )
        ]

    monkeypatch.setenv("INKVAULT_ENABLE_WEB_ASSIST", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(WebRawImportService, "assist_from_query", fake_assist)
    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    response = client.post(
        "/api/ask",
        json={
            "topicId": topic_id,
            "question": "这个主题的最新变化是什么？",
            "mode": "vault_plus_web",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["usedWebSources"] == [
        {
            "url": "https://example.com/new-evidence",
            "title": "New Evidence",
            "excerpt": "这条外部网页补足了最新变化的时间线证据。",
            "reasonUsed": "它补足了 vault 当前缺失的外部时间线来源。",
        }
    ]
    assert payload["canWriteback"] is True

    writeback = client.post(f"/api/ask/{payload['id']}/writeback")

    assert writeback.status_code == 200
    writeback_payload = writeback.json()
    assert writeback_payload["sourceId"] is not None
    assert writeback_payload["proposalPayload"]["evidence"][0]["locator"] == "https://example.com/new-evidence"


def test_repeated_ask_reconcile_keeps_chunk_index_idempotent(temp_app_env):
    from inkvault_server.db import session_scope
    from inkvault_server.models import RetrievalChunk

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    first_response = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "这个主题当前最重要的理解是什么？", "mode": "vault"},
    )
    assert first_response.status_code == 200

    with session_scope() as db:
        first_chunk_count = db.scalar(select(func.count(RetrievalChunk.id)).where(RetrievalChunk.entity_id == topic_id))

    second_response = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "继续看看这个主题当前最重要的理解", "mode": "vault"},
    )
    assert second_response.status_code == 200

    with session_scope() as db:
        second_chunk_count = db.scalar(select(func.count(RetrievalChunk.id)).where(RetrievalChunk.entity_id == topic_id))

    assert first_chunk_count == second_chunk_count


def test_web_import_service_assist_from_query_builds_results_from_search_candidates(monkeypatch):
    from inkvault_server.importers import ImportedRawMaterial, WebRawImportService

    service = WebRawImportService()
    monkeypatch.setattr(
        service,
        "_search_result_candidates",
        lambda _query: [
            ("https://example.com/a", "Result A"),
            ("https://example.com/b", "Result B"),
        ],
    )
    monkeypatch.setattr(
        service,
        "import_from_url",
        lambda url, title: ImportedRawMaterial(
            kind="WEB",
            title=title or url,
            locator=url,
            excerpt=f"{title} excerpt",
            body=f"{title} body",
        ),
    )

    results = service.assist_from_query("量子检索现在还缺什么证据？")

    assert [item.url for item in results] == ["https://example.com/a", "https://example.com/b"]
    assert results[0].title == "Result A"
    assert results[0].excerpt == "Result A excerpt"
    assert "量子检索现在还缺什么证据？" in results[0].reason_used
