CREATE TABLE plans (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces (id),
    title VARCHAR(240) NOT NULL,
    summary TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    horizon VARCHAR(20) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    focus_label VARCHAR(120) NOT NULL,
    next_step TEXT NOT NULL,
    next_action_label VARCHAR(120) NOT NULL,
    next_action_href VARCHAR(240) NOT NULL,
    search_term VARCHAR(160),
    agent_prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE plan_notes (
    plan_id VARCHAR(64) NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
    note_id VARCHAR(64) NOT NULL REFERENCES content_nodes (id) ON DELETE CASCADE,
    PRIMARY KEY (plan_id, note_id)
);

CREATE INDEX idx_plans_workspace_id ON plans (workspace_id);
CREATE INDEX idx_plans_status ON plans (status);
CREATE INDEX idx_plans_horizon ON plans (horizon);
CREATE INDEX idx_plan_notes_note_id ON plan_notes (note_id);
