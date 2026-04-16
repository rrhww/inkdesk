CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(120) NOT NULL UNIQUE,
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

CREATE TABLE content_nodes (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id),
    parent_id VARCHAR(64) REFERENCES content_nodes (id),
    type VARCHAR(20) NOT NULL,
    title VARCHAR(240) NOT NULL,
    sort_order INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE note_documents (
    id VARCHAR(64) PRIMARY KEY,
    note_id VARCHAR(64) NOT NULL UNIQUE REFERENCES content_nodes (id) ON DELETE CASCADE,
    markdown_content TEXT NOT NULL,
    excerpt TEXT,
    word_count INTEGER NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE tags (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(160) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_tags_workspace_name UNIQUE (workspace_id, name),
    CONSTRAINT uq_tags_workspace_slug UNIQUE (workspace_id, slug)
);

CREATE TABLE note_tags (
    note_id VARCHAR(64) NOT NULL REFERENCES content_nodes (id) ON DELETE CASCADE,
    tag_id VARCHAR(64) NOT NULL REFERENCES tags (id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

CREATE TABLE publications (
    id VARCHAR(64) PRIMARY KEY,
    note_id VARCHAR(64) NOT NULL UNIQUE REFERENCES content_nodes (id) ON DELETE CASCADE,
    slug VARCHAR(160) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_workspaces_owner_user_id ON workspaces (owner_user_id);
CREATE INDEX idx_content_nodes_workspace_id ON content_nodes (workspace_id);
CREATE INDEX idx_content_nodes_parent_id ON content_nodes (parent_id);
CREATE INDEX idx_content_nodes_workspace_parent_sort_order ON content_nodes (workspace_id, parent_id, sort_order);
CREATE INDEX idx_note_documents_note_id ON note_documents (note_id);
CREATE INDEX idx_tags_workspace_id ON tags (workspace_id);
CREATE INDEX idx_note_tags_tag_id ON note_tags (tag_id);
CREATE INDEX idx_publications_status ON publications (status);
