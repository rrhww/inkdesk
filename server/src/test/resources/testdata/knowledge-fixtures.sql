INSERT INTO users (id, username, email, password_hash, status, created_at, updated_at)
VALUES ('user-owner', 'owner', 'owner@inkdesk.local', '$2a$10$eV3G/Cflh.FS4xBtcOAxwOVImBnbvYWCUYaziOo05TGNBKLGQA6AK', 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00');

INSERT INTO workspaces (id, owner_user_id, name, slug, created_at, updated_at)
VALUES ('workspace-inkdesk', 'user-owner', 'Inkdesk', 'inkdesk', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00');

INSERT INTO workspace_settings (
    workspace_id,
    display_name,
    public_title,
    summary,
    public_location,
    default_page,
    compact_mode,
    show_context_ribbon,
    editor_default_view,
    editor_auto_save,
    editor_publish_reminder,
    publish_default_audience,
    publish_show_provenance,
    publish_highlight_recent_updates,
    created_at,
    updated_at
)
VALUES (
    'workspace-inkdesk',
    'R',
    '构建超级个人工作台的人',
    '我把 Inkdesk 当成自己的长期知识与执行系统，并持续向公共面输出成熟内容。',
    'Shanghai',
    '/app',
    FALSE,
    TRUE,
    'edit',
    TRUE,
    TRUE,
    'public',
    TRUE,
    TRUE,
    TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00',
    TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'
);

INSERT INTO content_nodes (id, workspace_id, parent_id, type, title, sort_order, status, created_at, updated_at)
VALUES
    ('folder-product-reframe', 'workspace-inkdesk', NULL, 'FOLDER', '产品重构', 100, 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('folder-system-structure', 'workspace-inkdesk', NULL, 'FOLDER', '主系统结构', 200, 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('folder-public-design', 'workspace-inkdesk', NULL, 'FOLDER', '公共面设计', 300, 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('note-001', 'workspace-inkdesk', 'folder-product-reframe', 'NOTE', '把 Inkdesk 从知识库改造成超级个人工作台', 110, 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 08:10:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:10:00+00'),
    ('note-002', 'workspace-inkdesk', 'folder-system-structure', 'NOTE', '为什么主系统首页必须先看到 Agent', 210, 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 07:42:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 07:42:00+00'),
    ('note-003', 'workspace-inkdesk', 'folder-public-design', 'NOTE', '公共博客页作为作者门户的结构草案', 310, 'ACTIVE', TIMESTAMP WITH TIME ZONE '2026-04-12 06:58:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 06:58:00+00');

INSERT INTO note_documents (id, note_id, markdown_content, excerpt, word_count, updated_at)
VALUES
    ('doc-001', 'note-001', '# 把 Inkdesk 从知识库改造成超级个人工作台

新的 Inkdesk 不再只是个人知识库加发布站，而是一个双面系统。

这意味着主系统首页不该再只是最近笔记列表，而要成为帮助我判断、组织和推进工作的中枢。', '重新定义公共面、主系统、Agent 控制台和任务计划在整个产品中的位置。', 1120, TIMESTAMP WITH TIME ZONE '2026-04-12 08:10:00+00'),
    ('doc-002', 'note-002', '# 为什么主系统首页必须先看到 Agent

如果首页先看到的只是文档列表，系统会退化成存储工具。

Agent 首页的作用是把知识、任务和上下文重新编排。', '记录 Agent 控制台为何要成为主人进入系统后的第一屏，而不是笔记列表或发布页。', 860, TIMESTAMP WITH TIME ZONE '2026-04-12 07:42:00+00'),
    ('doc-003', 'note-003', '# 公共博客页作为作者门户的结构草案

公共面是别人理解作者与公开内容的入口，而不是进入私有系统的入口。', '公共面应该同时承载公开文章、作者介绍和长期项目入口，而不是产品官网式 landing page。', 640, TIMESTAMP WITH TIME ZONE '2026-04-12 06:58:00+00');

INSERT INTO tags (id, workspace_id, name, slug, created_at)
VALUES
    ('tag-positioning', 'workspace-inkdesk', '定位', 'positioning', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-super-workbench', 'workspace-inkdesk', '超级个人工作台', 'super-workbench', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-agent', 'workspace-inkdesk', 'Agent', 'agent', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-homepage', 'workspace-inkdesk', '首页', 'homepage', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-system-design', 'workspace-inkdesk', '系统设计', 'system-design', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-public', 'workspace-inkdesk', '公共面', 'public-surface', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-blog', 'workspace-inkdesk', '博客', 'blog', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00'),
    ('tag-author-portal', 'workspace-inkdesk', '作者门户', 'author-portal', TIMESTAMP WITH TIME ZONE '2026-04-12 08:00:00+00');

INSERT INTO note_tags (note_id, tag_id)
VALUES
    ('note-001', 'tag-positioning'),
    ('note-001', 'tag-super-workbench'),
    ('note-001', 'tag-agent'),
    ('note-002', 'tag-agent'),
    ('note-002', 'tag-homepage'),
    ('note-002', 'tag-system-design'),
    ('note-003', 'tag-public'),
    ('note-003', 'tag-blog'),
    ('note-003', 'tag-author-portal');

INSERT INTO publications (id, note_id, slug, status, published_at, updated_at)
VALUES
    ('pub-001', 'note-001', 'super-personal-workbench-reframe', 'PUBLISHED', TIMESTAMP WITH TIME ZONE '2026-04-12 08:20:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 08:20:00+00'),
    ('pub-002', 'note-002', 'why-agent-first', 'DRAFT', NULL, TIMESTAMP WITH TIME ZONE '2026-04-12 07:50:00+00'),
    ('pub-003', 'note-003', 'public-blog-author-portal', 'PUBLISHED', TIMESTAMP WITH TIME ZONE '2026-04-12 07:05:00+00', TIMESTAMP WITH TIME ZONE '2026-04-12 07:05:00+00');
