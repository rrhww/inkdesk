from __future__ import annotations

from base64 import b64decode
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select


SAMPLE_PDF = b64decode(
    "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWyA0IDAgUiBdCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Ci9Gb250IDw8Ci9GMSA1IDAgUgo+Pgo+PgovTWVkaWFCb3ggWyAwLjAgMC4wIDMwMCAxNDQgXQovUGFyZW50IDIgMCBSCi9Db250ZW50cyA2IDAgUgo+PgplbmRvYmoKNSAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0xlbmd0aCA1Ngo+PgpzdHJlYW0KQlQKL0YxIDE4IFRmCjM2IDk2IFRkCihUb3BpYyBtZW1vcnkgbmVlZHMgcmV2aWV3LikgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDA1NCAwMDAwMCBuIAowMDAwMDAwMTEzIDAwMDAwIG4gCjAwMDAwMDAxNjIgMDAwMDAgbiAKMDAwMDAwMDI5NCAwMDAwMCBuIAowMDAwMDAwMzY0IDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNwovUm9vdCAzIDAgUgovSW5mbyAxIDAgUgo+PgpzdGFydHhyZWYKNDcwCiUlRU9GCg=="
)


def owner_client(temp_app_env: Path) -> TestClient:
    from inkdesk_server.main import create_app

    client = TestClient(create_app())
    client.cookies.set("inkdesk_owner_session", "owner")
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


def test_dashboard_includes_derived_knowledge_health_counts(temp_app_env):
    client = owner_client(temp_app_env)

    response = client.get("/api/admin/home")

    assert response.status_code == 200
    payload = response.json()
    health = payload["health"]
    assert health["rawBacklogCount"] == 3
    assert health["reviewBacklogCount"] == 3
    assert health["openQuestionCount"] == 0
    assert health["knowledgeGapCount"] == 0
    assert health["writebackCandidateCount"] == 0
    assert health["unsupportedClaimCount"] == 0
    assert {signal["type"] for signal in health["signals"]} >= {"RAW_BACKLOG", "REVIEW_BACKLOG"}

    review_id = payload["pendingReviews"][0]["id"]
    accept_response = client.post(f"/api/ingest/{review_id}/accept")
    assert accept_response.status_code == 200

    updated_payload = client.get("/api/admin/home").json()
    updated_health = updated_payload["health"]
    assert updated_health["openQuestionCount"] >= 1
    assert any(signal["type"] == "OPEN_QUESTIONS" for signal in updated_health["signals"])


def test_dashboard_health_surfaces_recent_ask_knowledge_gaps(temp_app_env):
    client = owner_client(temp_app_env)
    client.get("/api/admin/home")

    ask_response = client.post(
        "/api/ask",
        json={"question": "现在有哪些待审阅的研究迁移项？", "mode": "vault"},
    )
    assert ask_response.status_code == 200
    ask_payload = ask_response.json()
    assert ask_payload["knowledgeGaps"]

    dashboard_payload = client.get("/api/admin/home").json()
    health = dashboard_payload["health"]
    gap_signal = next(signal for signal in health["signals"] if signal["type"] == "KNOWLEDGE_GAP")

    assert health["knowledgeGapCount"] >= len(ask_payload["knowledgeGaps"])
    assert gap_signal["relatedId"] == ask_payload["id"]
    assert gap_signal["relatedTitle"] == ask_payload["question"]
    assert ask_payload["knowledgeGaps"][0] in gap_signal["summary"]


def test_dashboard_health_surfaces_ask_writeback_candidates(temp_app_env):
    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    ask_response = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "这个回答值得沉淀到 wiki 吗？", "mode": "vault"},
    )
    assert ask_response.status_code == 200
    ask_payload = ask_response.json()
    assert ask_payload["canWriteback"] is True

    dashboard_payload = client.get("/api/admin/home").json()
    health = dashboard_payload["health"]
    writeback_signal = next(signal for signal in health["signals"] if signal["type"] == "WRITEBACK_CANDIDATE")

    assert health["writebackCandidateCount"] >= 1
    assert writeback_signal["relatedId"] == ask_payload["id"]
    assert writeback_signal["relatedTitle"] == ask_payload["question"]


def test_dashboard_health_does_not_count_materialized_ask_writeback_candidates(temp_app_env):
    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]
    ask_payload = client.post(
        "/api/ask",
        json={"topicId": topic_id, "question": "这条结论进入 ingest 后还算候选吗？", "mode": "vault"},
    ).json()

    assert client.get("/api/admin/home").json()["health"]["writebackCandidateCount"] >= 1

    writeback_response = client.post(f"/api/ask/{ask_payload['id']}/writeback")
    assert writeback_response.status_code == 200

    health = client.get("/api/admin/home").json()["health"]
    assert health["writebackCandidateCount"] == 0
    assert all(signal["type"] != "WRITEBACK_CANDIDATE" for signal in health["signals"])


def test_ask_briefing_endpoint_returns_workspace_summary_by_default(temp_app_env):
    client = owner_client(temp_app_env)

    response = client.get("/api/ask/briefing")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "workspace"
    assert payload["summary"]
    assert payload["knowledgeGaps"]
    assert payload["nextActions"]
    assert payload["suggestedQuestions"]
    assert "generatedAt" in payload


def test_ask_briefing_endpoint_returns_topic_scoped_summary(temp_app_env):
    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    response = client.get("/api/ask/briefing", params={"topicId": topic_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "topic"
    assert payload["topicId"] == topic_id
    assert payload["topicTitle"]


def test_dashboard_health_and_briefing_surface_unsupported_claims(temp_app_env):
    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        claim.source_id = None
        claim.evidence_count = 0
        claim.provenance_status = "unsupported"
        claim.last_verified_at = None
        db.add(claim)

    dashboard_payload = client.get("/api/admin/home").json()
    health = dashboard_payload["health"]
    unsupported_signal = next(signal for signal in health["signals"] if signal["type"] == "UNSUPPORTED_CLAIM")

    assert health["unsupportedClaimCount"] == 1
    assert unsupported_signal["relatedId"] == topic_id
    assert unsupported_signal["relatedTitle"]

    briefing_payload = client.get("/api/ask/briefing").json()
    assert any(signal["type"] == "UNSUPPORTED_CLAIM" for signal in briefing_payload["supportingSignals"])
    assert any("claim" in gap["title"] or "证据" in gap["detail"] for gap in briefing_payload["knowledgeGaps"])


def test_wiki_topic_summaries_surface_claim_risk_counts(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        claim.evidence_count = 0
        claim.provenance_status = "unsupported"
        claim.usage_count = 4
        claim.last_used_at = datetime.now(UTC)
        claim.last_verified_at = datetime.now(UTC) - timedelta(days=90)
        db.add(claim)

    topics_payload = client.get("/api/wiki").json()
    topic_summary = next(topic for topic in topics_payload if topic["id"] == topic_id)

    assert topic_summary["unsupportedClaimCount"] == 1
    assert topic_summary["staleClaimCount"] == 1


def test_topic_scoped_ask_records_claim_usage_on_existing_claims(temp_app_env):
    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        claim_before = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim_before is not None
        assert getattr(claim_before, "usage_count", 0) == 0
        assert getattr(claim_before, "last_used_at", None) is None

    ask_response = client.post(
        "/api/ask",
        json={
            "topicId": topic_id,
            "question": "这个主题当前最重要的理解是什么？",
            "mode": "vault",
        },
    )
    assert ask_response.status_code == 200

    with session_scope() as db:
        claim_after = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim_after is not None
        assert claim_after.usage_count == 1
        assert claim_after.last_used_at is not None

    topic_payload = client.get(f"/api/wiki/{topic_id}").json()
    assert topic_payload["keyClaims"][0]["usageCount"] == 1
    assert topic_payload["keyClaims"][0]["lastUsedAt"] is not None


def test_global_ask_records_claim_usage_for_cited_topics(temp_app_env):
    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        claim_before = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim_before is not None
        assert claim_before.usage_count == 0

    ask_response = client.post(
        "/api/ask",
        json={
            "question": "现在有哪些待审阅的研究迁移项？",
            "mode": "vault",
        },
    )
    assert ask_response.status_code == 200
    ask_payload = ask_response.json()
    assert topic_id in ask_payload["usedWikiIds"]

    with session_scope() as db:
        claim_after = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim_after is not None
        assert claim_after.usage_count == 1
        assert claim_after.last_used_at is not None


def test_dashboard_health_surfaces_stale_claims_when_recently_used_claim_lacks_fresh_verification(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]
    ask_response = client.post(
        "/api/ask",
        json={
            "topicId": topic_id,
            "question": "这个主题当前最重要的理解是什么？",
            "mode": "vault",
        },
    )
    assert ask_response.status_code == 200

    with session_scope() as db:
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        claim.usage_count = 3
        claim.last_used_at = datetime.now(UTC)
        claim.last_verified_at = datetime.now(UTC) - timedelta(days=45)
        claim.provenance_status = "partial"
        db.add(claim)

    dashboard_payload = client.get("/api/admin/home").json()
    health = dashboard_payload["health"]
    stale_signal = next(signal for signal in health["signals"] if signal["type"] == "STALE_CLAIM")

    assert health["staleClaimCount"] == 1
    assert stale_signal["relatedId"] == topic_id
    assert stale_signal["relatedTitle"]

    briefing_payload = client.get("/api/ask/briefing").json()
    assert any(signal["type"] == "STALE_CLAIM" for signal in briefing_payload["supportingSignals"])
    assert any("重审" in action["label"] or "复核" in action["description"] for action in briefing_payload["nextActions"])


def test_dashboard_health_briefing_and_topic_detail_surface_conflicting_claims(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        now = datetime.now(UTC)
        claim.statement = "首页应该先呈现 Ask 工作区。"
        claim.evidence_count = 2
        claim.provenance_status = "supported"
        claim.last_verified_at = now
        claim.updated_at = now
        db.add(claim)
        db.add(
            TopicClaim(
                id="claim-conflict-001",
                topic_id=topic_id,
                source_id=claim.source_id,
                statement="首页不应该先呈现 Ask 工作区。",
                citation_label=claim.citation_label,
                evidence_count=0,
                provenance_status="unsupported",
                last_verified_at=now - timedelta(days=5),
                updated_at=now - timedelta(days=5),
                usage_count=1,
                last_used_at=now - timedelta(days=1),
                sort_order=(claim.sort_order or 0) + 1,
                created_at=now - timedelta(days=5),
            )
        )

    dashboard_payload = client.get("/api/admin/home").json()
    health = dashboard_payload["health"]
    conflict_signal = next(signal for signal in health["signals"] if signal["type"] == "CONFLICTING_CLAIM")

    assert health["conflictingClaimCount"] == 2
    assert conflict_signal["relatedId"] == topic_id
    assert conflict_signal["relatedTitle"]

    briefing_payload = client.get("/api/ask/briefing").json()
    assert any(signal["type"] == "CONFLICTING_CLAIM" for signal in briefing_payload["supportingSignals"])
    assert any("冲突" in gap["title"] or "冲突" in gap["detail"] for gap in briefing_payload["knowledgeGaps"])
    assert any("冲突" in action["label"] or "冲突" in action["description"] for action in briefing_payload["nextActions"])

    topic_payload = client.get(f"/api/wiki/{topic_id}").json()
    conflicting_claims = [claim for claim in topic_payload["keyClaims"] if claim["hasConflict"]]
    assert len(conflicting_claims) == 2


def test_used_stale_claim_materializes_re_review_item_without_creating_duplicate(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.models import TopicClaim
    from inkdesk_server.research import get_research_service
    from inkdesk_server.core.config import get_settings

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        claim.usage_count = 4
        claim.last_used_at = datetime.now(UTC)
        claim.last_verified_at = datetime.now(UTC) - timedelta(days=60)
        claim.provenance_status = "partial"
        db.add(claim)

        created_review = service.ensure_claim_review_for_topic(topic_id)
        assert created_review is not None
        assert created_review.kind == "TOPIC_PATCH"
        assert created_review.targetTopicId == topic_id
        assert "重审" in created_review.title or "复核" in created_review.title
        assert created_review.proposalPayload.topicDecision.decision == "PATCH"
        assert created_review.proposalPayload.claims
        assert created_review.proposalPayload.claims[0].statement == claim.statement
        assert created_review.proposalPayload.claims[0].provenanceStatus == "partial"
        assert created_review.proposalPayload.claims[0].usageCount == 4
        assert created_review.proposalPayload.claims[0].lastUsedAt is not None
        assert created_review.proposalPayload.claims[0].lastVerifiedAt is not None
        assert created_review.proposalPayload.openQuestions
        assert any("重审" in item or "复核" in item for item in created_review.proposalPayload.openQuestions)

        duplicate_review = service.ensure_claim_review_for_topic(topic_id)
        assert duplicate_review is not None
        assert duplicate_review.id == created_review.id


def test_accepting_stale_claim_review_refreshes_existing_claim_and_clears_repeat_staleness(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.models import TopicClaim
    from inkdesk_server.research import get_research_service
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.time_utils import ensure_utc_datetime

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        claim.usage_count = 5
        claim.last_used_at = datetime.now(UTC)
        claim.last_verified_at = datetime.now(UTC) - timedelta(days=90)
        claim.provenance_status = "partial"
        original_claim_id = claim.id
        db.add(claim)

        stale_review = service.ensure_claim_review_for_topic(topic_id)
        assert stale_review is not None

        service.accept_review(stale_review.id)
        refreshed = db.scalar(select(TopicClaim).where(TopicClaim.id == original_claim_id))
        assert refreshed is not None
        assert refreshed.last_verified_at is not None
        assert ensure_utc_datetime(refreshed.last_verified_at) > datetime.now(UTC) - timedelta(minutes=1)
        assert refreshed.id == original_claim_id

        topic_payload = service.get_topic(topic_id)
        refreshed_claim = next(claim for claim in topic_payload.keyClaims if claim.id == original_claim_id)
        assert refreshed_claim.lastVerifiedAt is not None
        assert ensure_utc_datetime(refreshed_claim.lastVerifiedAt) > datetime.now(UTC) - timedelta(minutes=1)

        dashboard_payload = service.get_dashboard()
        assert dashboard_payload.health.staleClaimCount == 0
        assert all(signal.type != "STALE_CLAIM" for signal in dashboard_payload.health.signals)

        briefing_payload = service.get_ask_briefing(topic_id=topic_id)
        assert all(signal.type != "STALE_CLAIM" for signal in briefing_payload.supportingSignals)
        assert all("需要重审" not in gap.title for gap in briefing_payload.knowledgeGaps)

        pending_repeat = service.ensure_claim_review_for_topic(topic_id)
        assert pending_repeat is None

def test_stale_claim_review_appears_in_ingest_after_health_materialization(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert claim is not None
        claim.usage_count = 4
        claim.last_used_at = datetime.now(UTC)
        claim.last_verified_at = datetime.now(UTC) - timedelta(days=90)
        claim.provenance_status = "partial"
        db.add(claim)

    client.get("/api/admin/home")
    ingest_payload = client.get("/api/ingest").json()
    stale_review = next(review for review in ingest_payload if "重审" in review["title"] or "复核" in review["summary"])

    assert stale_review["targetTopicId"] == topic_id
    assert stale_review["proposalPayload"]["topicDecision"]["decision"] == "PATCH"
    assert stale_review["proposalPayload"]["claims"][0]["usageCount"] == 4
    assert stale_review["proposalPayload"]["claims"][0]["lastUsedAt"] is not None
    assert stale_review["proposalPayload"]["claims"][0]["lastVerifiedAt"] is not None
    assert stale_review["proposalPayload"]["claims"][0]["needsReview"] is True


def test_conflicting_claim_review_materializes_without_creating_duplicate(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.models import TopicClaim
    from inkdesk_server.research import get_research_service
    from inkdesk_server.core.config import get_settings

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId
        canonical_claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert canonical_claim is not None
        now = datetime.now(UTC)
        canonical_claim.statement = "首页应该先呈现 Ask 工作区。"
        canonical_claim.evidence_count = 2
        canonical_claim.provenance_status = "supported"
        canonical_claim.last_verified_at = now
        canonical_claim.updated_at = now
        db.add(canonical_claim)
        db.add(
            TopicClaim(
                id="claim-conflict-002",
                topic_id=topic_id,
                source_id=canonical_claim.source_id,
                statement="首页不应该先呈现 Ask 工作区。",
                citation_label=canonical_claim.citation_label,
                evidence_count=0,
                provenance_status="unsupported",
                last_verified_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=10),
                usage_count=1,
                last_used_at=now - timedelta(days=1),
                sort_order=(canonical_claim.sort_order or 0) + 1,
                created_at=now - timedelta(days=10),
            )
        )

        created_review = service.ensure_conflict_review_for_topic(topic_id)
        assert created_review is not None
        assert created_review.kind == "TOPIC_PATCH"
        assert created_review.targetTopicId == topic_id
        assert "冲突" in created_review.title or "冲突" in created_review.summary
        assert created_review.proposalPayload.topicDecision.decision == "PATCH"
        assert created_review.proposalPayload.claims
        assert created_review.proposalPayload.claims[0].statement == canonical_claim.statement
        assert created_review.proposalPayload.claims[0].hasConflict is True
        assert created_review.proposalPayload.conflicts
        assert any("冲突" in item for item in created_review.proposalPayload.conflicts)

        duplicate_review = service.ensure_conflict_review_for_topic(topic_id)
        assert duplicate_review is not None
        assert duplicate_review.id == created_review.id


def test_accepting_conflict_review_keeps_canonical_claim_and_clears_repeat_conflict(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.models import TopicClaim
    from inkdesk_server.research import get_research_service
    from inkdesk_server.core.config import get_settings

    init_db()
    with session_scope() as db:
        service = get_research_service(db, get_settings())
        first_review = service.get_review_items()[0]
        topic_id = service.accept_review(first_review.id).topicId
        canonical_claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert canonical_claim is not None
        now = datetime.now(UTC)
        canonical_claim.statement = "首页应该先呈现 Ask 工作区。"
        canonical_claim.evidence_count = 2
        canonical_claim.provenance_status = "supported"
        canonical_claim.last_verified_at = now
        canonical_claim.updated_at = now
        canonical_claim_id = canonical_claim.id
        db.add(canonical_claim)
        db.add(
            TopicClaim(
                id="claim-conflict-003",
                topic_id=topic_id,
                source_id=canonical_claim.source_id,
                statement="首页不应该先呈现 Ask 工作区。",
                citation_label=canonical_claim.citation_label,
                evidence_count=0,
                provenance_status="unsupported",
                last_verified_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=10),
                usage_count=1,
                last_used_at=now - timedelta(days=1),
                sort_order=(canonical_claim.sort_order or 0) + 1,
                created_at=now - timedelta(days=10),
            )
        )

        conflict_review = service.ensure_conflict_review_for_topic(topic_id)
        assert conflict_review is not None

        service.accept_review(conflict_review.id)
        topic_payload = service.get_topic(topic_id)
        claims_by_id = {claim.id: claim for claim in topic_payload.keyClaims}

        assert canonical_claim_id in claims_by_id
        assert len(topic_payload.keyClaims) == 1
        assert claims_by_id[canonical_claim_id].hasConflict is False

        dashboard_payload = service.get_dashboard()
        assert dashboard_payload.health.conflictingClaimCount == 0
        assert all(signal.type != "CONFLICTING_CLAIM" for signal in dashboard_payload.health.signals)

        briefing_payload = service.get_ask_briefing(topic_id=topic_id)
        assert all(signal.type != "CONFLICTING_CLAIM" for signal in briefing_payload.supportingSignals)
        assert all("冲突" not in gap.title and "冲突" not in gap.detail for gap in briefing_payload.knowledgeGaps)

        pending_repeat = service.ensure_conflict_review_for_topic(topic_id)
        assert pending_repeat is None


def test_conflicting_claim_review_appears_in_ingest_after_health_materialization(temp_app_env):
    from datetime import UTC, datetime, timedelta

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import TopicClaim

    client = owner_client(temp_app_env)
    initial_reviews = client.get("/api/ingest").json()
    topic_id = client.post(f"/api/ingest/{initial_reviews[0]['id']}/accept").json()["topicId"]

    with session_scope() as db:
        canonical_claim = db.scalar(select(TopicClaim).where(TopicClaim.topic_id == topic_id))
        assert canonical_claim is not None
        now = datetime.now(UTC)
        canonical_claim.statement = "首页应该先呈现 Ask 工作区。"
        canonical_claim.evidence_count = 2
        canonical_claim.provenance_status = "supported"
        canonical_claim.last_verified_at = now
        canonical_claim.updated_at = now
        db.add(canonical_claim)
        db.add(
            TopicClaim(
                id="claim-conflict-004",
                topic_id=topic_id,
                source_id=canonical_claim.source_id,
                statement="首页不应该先呈现 Ask 工作区。",
                citation_label=canonical_claim.citation_label,
                evidence_count=0,
                provenance_status="unsupported",
                last_verified_at=now - timedelta(days=7),
                updated_at=now - timedelta(days=7),
                usage_count=1,
                last_used_at=now - timedelta(days=1),
                sort_order=(canonical_claim.sort_order or 0) + 1,
                created_at=now - timedelta(days=7),
            )
        )

    client.get("/api/admin/home")
    ingest_payload = client.get("/api/ingest").json()
    conflict_review = next(review for review in ingest_payload if "冲突" in review["title"] or "冲突" in review["summary"])

    assert conflict_review["targetTopicId"] == topic_id
    assert conflict_review["proposalPayload"]["topicDecision"]["decision"] == "PATCH"
    assert conflict_review["proposalPayload"]["claims"][0]["statement"] == "首页应该先呈现 Ask 工作区。"
    assert conflict_review["proposalPayload"]["claims"][0]["hasConflict"] is True
    assert conflict_review["proposalPayload"]["conflicts"]


def test_ask_briefing_endpoint_returns_ask_turn_scoped_summary_and_persists_payload(temp_app_env):
    client = owner_client(temp_app_env)
    ask_payload = client.post(
        "/api/ask",
        json={"question": "现在有哪些待审阅的研究迁移项？", "mode": "vault"},
    ).json()

    response = client.get("/api/ask/briefing", params={"askTurnId": ask_payload["id"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "ask_turn"
    assert payload["askTurnId"] == ask_payload["id"]
    assert payload["knowledgeGaps"]

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import AskTurn

    with session_scope() as db:
        stored_turn = db.scalar(select(AskTurn).where(AskTurn.id == ask_payload["id"]))
        assert stored_turn is not None
        assert stored_turn.judgment_payload_json != "{}"


def test_ask_briefing_endpoint_recomputes_missing_judgment_payload_for_legacy_turn(temp_app_env):
    client = owner_client(temp_app_env)
    ask_payload = client.post(
        "/api/ask",
        json={"question": "现在有哪些待审阅的研究迁移项？", "mode": "vault"},
    ).json()

    from inkdesk_server.db import session_scope
    from inkdesk_server.models import AskTurn

    with session_scope() as db:
        stored_turn = db.scalar(select(AskTurn).where(AskTurn.id == ask_payload["id"]))
        assert stored_turn is not None
        stored_turn.judgment_payload_json = "{}"
        db.add(stored_turn)

    response = client.get("/api/ask/briefing", params={"askTurnId": ask_payload["id"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "ask_turn"
    assert payload["summary"]


def test_raw_import_and_wiki_accept_flow(temp_app_env):
    client = owner_client(temp_app_env)

    create_response = client.post(
        "/api/raw",
        json={
            "kind": "WEB",
            "title": "将 Inkdesk 重定位为私有研究型 LLM Wiki：外部评注",
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
    from inkdesk_server.agents import CompileClaimModel, CompileResponseModel
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.research import get_research_service

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
        assert review.proposalPayload.claims[0].supportingChunkIds == review.proposalPayload.claims[0].citationChunkIds
        assert review.proposalPayload.claims[0].evidenceCount == 1
        assert review.proposalPayload.claims[0].provenanceStatus == "supported"
        assert review.proposalPayload.conflicts == ["旧的个人操作系统叙事需要继续降权。"]
        assert review.proposalPayload.openQuestions == ["还缺少哪条外部对照来源？"]
        assert review.proposalPayload.explanation == "因为检索到的 wiki chunk 与新 raw 材料高度一致，所以更适合走 PATCH。"
        assert review.proposalPayload.evidence[0].chunkId
        assert review.proposalPayload.evidence[0].entityType == "TOPIC"


def test_accept_review_applies_all_structured_claims_and_open_questions_to_topic(temp_app_env):
    from inkdesk_server.agents import CompileClaimModel, CompileResponseModel
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.research import get_research_service

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

        claims_by_statement = {claim.statement: claim for claim in topic.keyClaims}
        assert "新的 raw 材料支持现有 wiki 主题。" in claims_by_statement
        assert "产品主路径需要继续压缩到 research-first workflow。" in claims_by_statement
        assert claims_by_statement["新的 raw 材料支持现有 wiki 主题。"].provenanceStatus == "supported"
        assert claims_by_statement["新的 raw 材料支持现有 wiki 主题。"].evidenceCount == 1
        assert claims_by_statement["新的 raw 材料支持现有 wiki 主题。"].lastVerifiedAt is not None
        assert "还缺少哪条外部对照来源？" in topic.openQuestions
        assert "是否需要补一条迁移说明？" in topic.openQuestions


def test_accept_topic_create_review_applies_structured_payload_to_new_topic(temp_app_env):
    from inkdesk_server.agents import CompileClaimModel, CompileResponseModel
    from inkdesk_server.core.config import get_settings
    from inkdesk_server.db import init_db, session_scope
    from inkdesk_server.research import get_research_service

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
        claims_by_statement = {claim.statement: claim for claim in topic.keyClaims}
        assert "研究记忆系统需要保留人工审阅环节。" in claims_by_statement
        assert "Ask 的高质量回答应该可以转成可审阅提案。" in claims_by_statement
        assert claims_by_statement["研究记忆系统需要保留人工审阅环节。"].provenanceStatus == "partial"
        assert claims_by_statement["研究记忆系统需要保留人工审阅环节。"].evidenceCount == 1
        assert claims_by_statement["研究记忆系统需要保留人工审阅环节。"].lastVerifiedAt is not None
        assert "首个版本是否需要默认联网补证？" in topic.openQuestions
        assert "是否保留更细粒度 claim 级 accept？" in topic.openQuestions


def test_vault_plus_web_ask_surfaces_external_web_assist_results_but_keeps_writeback_explicit(temp_app_env, monkeypatch):
    from inkdesk_server.importers import WebAssistResult, WebRawImportService
    from inkdesk_server.core.config import get_settings

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

    monkeypatch.setenv("INKDESK_ENABLE_WEB_ASSIST", "true")
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
    from inkdesk_server.db import session_scope
    from inkdesk_server.models import RetrievalChunk

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
    from inkdesk_server.importers import ImportedRawMaterial, WebRawImportService

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
