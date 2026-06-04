from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from inkdesk_server.core.config import get_settings


Base = declarative_base()


ASK_TURNS_SCHEMA_UPGRADES = (
    ("parent_ask_turn_id", "ALTER TABLE ask_turns ADD COLUMN parent_ask_turn_id VARCHAR(64) REFERENCES ask_turns (id) ON DELETE SET NULL"),
    ("thread_root_ask_turn_id", "ALTER TABLE ask_turns ADD COLUMN thread_root_ask_turn_id VARCHAR(64) REFERENCES ask_turns (id) ON DELETE SET NULL"),
    ("mode", "ALTER TABLE ask_turns ADD COLUMN mode VARCHAR(32) NOT NULL DEFAULT 'vault'"),
    ("confidence", "ALTER TABLE ask_turns ADD COLUMN confidence FLOAT NOT NULL DEFAULT 0"),
    ("retrieval_mode", "ALTER TABLE ask_turns ADD COLUMN retrieval_mode VARCHAR(32) NOT NULL DEFAULT 'lexical_fallback'"),
    ("used_wiki_ids", "ALTER TABLE ask_turns ADD COLUMN used_wiki_ids TEXT NOT NULL DEFAULT ''"),
    ("used_source_ids", "ALTER TABLE ask_turns ADD COLUMN used_source_ids TEXT NOT NULL DEFAULT ''"),
    ("used_chunk_ids", "ALTER TABLE ask_turns ADD COLUMN used_chunk_ids TEXT NOT NULL DEFAULT ''"),
    ("used_web_sources_json", "ALTER TABLE ask_turns ADD COLUMN used_web_sources_json TEXT NOT NULL DEFAULT '[]'"),
    ("knowledge_gaps_json", "ALTER TABLE ask_turns ADD COLUMN knowledge_gaps_json TEXT NOT NULL DEFAULT '[]'"),
    ("follow_up_questions_json", "ALTER TABLE ask_turns ADD COLUMN follow_up_questions_json TEXT NOT NULL DEFAULT '[]'"),
    ("can_writeback", "ALTER TABLE ask_turns ADD COLUMN can_writeback BOOLEAN NOT NULL DEFAULT 1"),
    ("writeback_package_json", "ALTER TABLE ask_turns ADD COLUMN writeback_package_json TEXT NOT NULL DEFAULT '{}'"),
    ("judgment_payload_json", "ALTER TABLE ask_turns ADD COLUMN judgment_payload_json TEXT NOT NULL DEFAULT '{}'"),
)

REVIEW_ITEMS_SCHEMA_UPGRADES = (
    ("proposal_payload_json", "ALTER TABLE review_items ADD COLUMN proposal_payload_json TEXT NOT NULL DEFAULT '{}'"),
)

TOPIC_CLAIMS_SCHEMA_UPGRADES = (
    ("evidence_count", "ALTER TABLE topic_claims ADD COLUMN evidence_count INTEGER NOT NULL DEFAULT 0"),
    ("provenance_status", "ALTER TABLE topic_claims ADD COLUMN provenance_status VARCHAR(20) NOT NULL DEFAULT 'unsupported'"),
    ("last_verified_at", "ALTER TABLE topic_claims ADD COLUMN last_verified_at TIMESTAMP NULL"),
    ("updated_at", "ALTER TABLE topic_claims ADD COLUMN updated_at TIMESTAMP NULL"),
    ("usage_count", "ALTER TABLE topic_claims ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0"),
    ("last_used_at", "ALTER TABLE topic_claims ADD COLUMN last_used_at TIMESTAMP NULL"),
)


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}
    return create_engine(settings.db_url, future=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def init_db() -> None:
    from inkdesk_server import models  # noqa: F401

    engine = get_engine()
    ensure_pgvector_extension(engine)
    Base.metadata.create_all(bind=engine)
    upgrade_existing_schema(engine)


def ensure_pgvector_extension(engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def upgrade_existing_schema(engine) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("ask_turns"):
            pass
        else:
            existing_columns = {column["name"] for column in inspector.get_columns("ask_turns")}
            for column_name, ddl in ASK_TURNS_SCHEMA_UPGRADES:
                if column_name in existing_columns:
                    continue
                connection.exec_driver_sql(ddl)
                existing_columns.add(column_name)

        if inspector.has_table("review_items"):
            review_columns = {column["name"] for column in inspector.get_columns("review_items")}
            for column_name, ddl in REVIEW_ITEMS_SCHEMA_UPGRADES:
                if column_name in review_columns:
                    continue
                connection.exec_driver_sql(ddl)
                review_columns.add(column_name)

        if inspector.has_table("topic_claims"):
            topic_claim_columns = {column["name"] for column in inspector.get_columns("topic_claims")}
            for column_name, ddl in TOPIC_CLAIMS_SCHEMA_UPGRADES:
                if column_name in topic_claim_columns:
                    continue
                connection.exec_driver_sql(ddl)
                topic_claim_columns.add(column_name)


def get_db() -> Session:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
