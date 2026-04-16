INSERT INTO users (id, username, email, password_hash, status, created_at, updated_at)
VALUES ('user-owner', 'owner', 'owner@inkdesk.local', '$2a$10$eV3G/Cflh.FS4xBtcOAxwOVImBnbvYWCUYaziOo05TGNBKLGQA6AK', 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00');

INSERT INTO workspaces (id, owner_user_id, name, slug, created_at, updated_at)
VALUES ('workspace-inkdesk', 'user-owner', 'Inkdesk', 'inkdesk', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00');
