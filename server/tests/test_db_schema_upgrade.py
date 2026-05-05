from __future__ import annotations

from sqlalchemy import text


def test_init_db_upgrades_legacy_ask_turns_schema_in_place(temp_app_env):
    from inkvault_server.db import get_engine, init_db

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE ask_turns (
                    id VARCHAR(64) PRIMARY KEY,
                    workspace_id VARCHAR(64) NOT NULL,
                    topic_id VARCHAR(64),
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citation_source_ids TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO ask_turns (id, workspace_id, topic_id, question, answer, citation_source_ids, created_at)
                VALUES ('ask-legacy', 'workspace-1', NULL, 'legacy question', 'legacy answer', 'source-1', '2026-04-13T08:45:00Z')
                """
            )
        )

    init_db()

    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    parent_ask_turn_id,
                    thread_root_ask_turn_id,
                    mode,
                    confidence,
                    retrieval_mode,
                    used_wiki_ids,
                    used_source_ids,
                    used_chunk_ids,
                    used_web_sources_json,
                    knowledge_gaps_json,
                    follow_up_questions_json,
                    can_writeback,
                    writeback_package_json
                FROM ask_turns
                WHERE id = 'ask-legacy'
                """
            )
        ).mappings().one()

    assert row["parent_ask_turn_id"] is None
    assert row["thread_root_ask_turn_id"] is None
    assert row["mode"] == "vault"
    assert row["confidence"] == 0
    assert row["retrieval_mode"] == "lexical_fallback"
    assert row["used_wiki_ids"] == ""
    assert row["used_source_ids"] == ""
    assert row["used_chunk_ids"] == ""
    assert row["used_web_sources_json"] == "[]"
    assert row["knowledge_gaps_json"] == "[]"
    assert row["follow_up_questions_json"] == "[]"
    assert row["can_writeback"] == 1
    assert row["writeback_package_json"] == "{}"


def test_init_db_upgrades_legacy_review_items_schema_in_place(temp_app_env):
    from inkvault_server.db import get_engine, init_db

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE review_items (
                    id VARCHAR(64) PRIMARY KEY,
                    workspace_id VARCHAR(64) NOT NULL,
                    kind VARCHAR(20) NOT NULL,
                    proposal_kind VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    title VARCHAR(240) NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO review_items (id, workspace_id, kind, proposal_kind, status, title, summary, created_at)
                VALUES ('review-legacy', 'workspace-1', 'TOPIC_CREATE', 'TOPIC_CREATE', 'PENDING', 'legacy review', 'legacy summary', '2026-04-13T08:45:00Z')
                """
            )
        )

    init_db()

    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT proposal_payload_json
                FROM review_items
                WHERE id = 'review-legacy'
                """
            )
        ).mappings().one()

    assert row["proposal_payload_json"] == "{}"
