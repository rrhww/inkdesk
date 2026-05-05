ALTER TABLE users
    ADD COLUMN email VARCHAR(255);

UPDATE users
SET email = username || '@inkvault.local'
WHERE email IS NULL;

ALTER TABLE users
    ALTER COLUMN email SET NOT NULL;

ALTER TABLE users
    ADD CONSTRAINT uq_users_email UNIQUE (email);

CREATE TABLE workspace_settings (
    workspace_id VARCHAR(64) PRIMARY KEY REFERENCES workspaces (id) ON DELETE CASCADE,
    display_name VARCHAR(120) NOT NULL,
    public_title VARCHAR(240) NOT NULL,
    summary TEXT NOT NULL,
    public_location VARCHAR(120) NOT NULL,
    default_page VARCHAR(120) NOT NULL,
    compact_mode BOOLEAN NOT NULL,
    show_context_ribbon BOOLEAN NOT NULL,
    editor_default_view VARCHAR(20) NOT NULL,
    editor_auto_save BOOLEAN NOT NULL,
    editor_publish_reminder BOOLEAN NOT NULL,
    publish_default_audience VARCHAR(20) NOT NULL,
    publish_show_provenance BOOLEAN NOT NULL,
    publish_highlight_recent_updates BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
