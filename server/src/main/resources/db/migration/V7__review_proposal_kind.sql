ALTER TABLE review_items
    ADD COLUMN proposal_kind VARCHAR(20);

UPDATE review_items
SET proposal_kind = CASE kind
    WHEN 'TOPIC_PATCH' THEN 'TOPIC_PATCH'
    ELSE 'TOPIC_CREATE'
END
WHERE proposal_kind IS NULL;

ALTER TABLE review_items
    ALTER COLUMN proposal_kind SET NOT NULL;
