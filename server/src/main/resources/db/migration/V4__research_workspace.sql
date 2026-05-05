CREATE TABLE sources (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    legacy_note_id VARCHAR(64) UNIQUE REFERENCES content_nodes (id) ON DELETE SET NULL,
    kind VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    title VARCHAR(240) NOT NULL,
    locator VARCHAR(500),
    excerpt TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE topics (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    title VARCHAR(240) NOT NULL,
    slug VARCHAR(180) NOT NULL,
    summary TEXT NOT NULL,
    current_understanding TEXT NOT NULL,
    open_questions TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_topics_workspace_slug UNIQUE (workspace_id, slug)
);

CREATE TABLE topic_sources (
    topic_id VARCHAR(64) NOT NULL REFERENCES topics (id) ON DELETE CASCADE,
    source_id VARCHAR(64) NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    PRIMARY KEY (topic_id, source_id)
);

CREATE TABLE topic_claims (
    id VARCHAR(64) PRIMARY KEY,
    topic_id VARCHAR(64) NOT NULL REFERENCES topics (id) ON DELETE CASCADE,
    source_id VARCHAR(64) REFERENCES sources (id) ON DELETE SET NULL,
    statement TEXT NOT NULL,
    citation_label VARCHAR(240) NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE topic_thread_entries (
    id VARCHAR(64) PRIMARY KEY,
    topic_id VARCHAR(64) NOT NULL REFERENCES topics (id) ON DELETE CASCADE,
    source_id VARCHAR(64) REFERENCES sources (id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE review_items (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    source_id VARCHAR(64) REFERENCES sources (id) ON DELETE SET NULL,
    target_topic_id VARCHAR(64) REFERENCES topics (id) ON DELETE SET NULL,
    kind VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    title VARCHAR(240) NOT NULL,
    summary TEXT NOT NULL,
    proposed_topic_title VARCHAR(240),
    proposed_understanding TEXT,
    proposed_open_questions TEXT,
    proposed_claim TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    decided_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE ask_turns (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    topic_id VARCHAR(64) REFERENCES topics (id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    citation_source_ids TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_sources_workspace_id ON sources (workspace_id);
CREATE INDEX idx_sources_status ON sources (status);
CREATE INDEX idx_topics_workspace_id ON topics (workspace_id);
CREATE INDEX idx_topic_claims_topic_id ON topic_claims (topic_id);
CREATE INDEX idx_topic_thread_entries_topic_id ON topic_thread_entries (topic_id);
CREATE INDEX idx_review_items_workspace_status ON review_items (workspace_id, status);
CREATE INDEX idx_review_items_source_id ON review_items (source_id);
CREATE INDEX idx_ask_turns_workspace_id ON ask_turns (workspace_id);
