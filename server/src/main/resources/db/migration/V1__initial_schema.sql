CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(120) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE workspaces (
    id VARCHAR(64) PRIMARY KEY,
    owner_user_id VARCHAR(64) NOT NULL REFERENCES users (id),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE retrieval_chunks (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    entity_type VARCHAR(20) NOT NULL,
    entity_id VARCHAR(256) NOT NULL,
    chunk_ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    content_hash VARCHAR(128) NOT NULL,
    embedding_json TEXT NOT NULL DEFAULT '[]',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_retrieval_chunk_ordinal UNIQUE (workspace_id, entity_type, entity_id, chunk_ordinal)
);

CREATE INDEX idx_retrieval_chunks_workspace_entity ON retrieval_chunks (workspace_id, entity_type, entity_id);
