ALTER TABLE sources ADD COLUMN vault_path VARCHAR(500);
ALTER TABLE sources ADD COLUMN content_hash VARCHAR(128);

ALTER TABLE topics ADD COLUMN vault_path VARCHAR(500);
ALTER TABLE topics ADD COLUMN content_hash VARCHAR(128);

ALTER TABLE review_items ADD COLUMN proposed_vault_path VARCHAR(500);
ALTER TABLE review_items ADD COLUMN content_hash VARCHAR(128);

UPDATE sources
SET status = CASE status
    WHEN 'INBOX' THEN 'INGEST_PENDING'
    WHEN 'LINKED' THEN 'WIKI_LINKED'
    WHEN 'DISMISSED' THEN 'IGNORED'
    ELSE status
END;

CREATE INDEX idx_sources_vault_path ON sources (vault_path);
CREATE INDEX idx_topics_vault_path ON topics (vault_path);
