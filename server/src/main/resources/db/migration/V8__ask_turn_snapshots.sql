ALTER TABLE ask_turns
    ADD COLUMN parent_ask_turn_id VARCHAR(64) REFERENCES ask_turns (id) ON DELETE SET NULL;

ALTER TABLE ask_turns
    ADD COLUMN mode VARCHAR(32) NOT NULL DEFAULT 'vault';

ALTER TABLE ask_turns
    ADD COLUMN used_wiki_ids TEXT NOT NULL DEFAULT '';

ALTER TABLE ask_turns
    ADD COLUMN used_source_ids TEXT NOT NULL DEFAULT '';

ALTER TABLE ask_turns
    ADD COLUMN used_web_sources_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE ask_turns
    ADD COLUMN knowledge_gaps_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE ask_turns
    ADD COLUMN follow_up_questions_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE ask_turns
    ADD COLUMN writeback_package_json TEXT NOT NULL DEFAULT '{}';
