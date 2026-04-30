package com.inkdesk.server.knowledge.service;

import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.NoteDocumentEntity;
import com.inkdesk.server.knowledge.persistence.PublicationEntity;
import com.inkdesk.server.knowledge.persistence.TagEntity;
import com.inkdesk.server.knowledge.persistence.TagRepository;
import com.inkdesk.server.knowledge.persistence.UserEntity;
import com.inkdesk.server.knowledge.persistence.UserRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import com.inkdesk.server.settings.WorkspaceSettingsEntity;
import com.inkdesk.server.settings.WorkspaceSettingsRepository;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Set;

@Component
@Profile("local")
@Order(10)
public class LocalKnowledgeSeedLoader implements ApplicationRunner {

    private final UserRepository userRepository;
    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceSettingsRepository workspaceSettingsRepository;
    private final TagRepository tagRepository;
    private final ContentNodeRepository contentNodeRepository;

    public LocalKnowledgeSeedLoader(
            UserRepository userRepository,
            WorkspaceRepository workspaceRepository,
            WorkspaceSettingsRepository workspaceSettingsRepository,
            TagRepository tagRepository,
            ContentNodeRepository contentNodeRepository
    ) {
        this.userRepository = userRepository;
        this.workspaceRepository = workspaceRepository;
        this.workspaceSettingsRepository = workspaceSettingsRepository;
        this.tagRepository = tagRepository;
        this.contentNodeRepository = contentNodeRepository;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        Instant now = Instant.parse("2026-04-12T08:00:00Z");

        UserEntity owner = userRepository.findByUsername("owner")
                .orElseGet(() -> userRepository.save(buildOwner(now)));

        WorkspaceEntity workspace = workspaceRepository.findById("workspace-inkdesk")
                .or(() -> workspaceRepository.findBySlug("inkdesk"))
                .or(() -> workspaceRepository.findByOwnerUserId(owner.getId()))
                .orElseGet(() -> workspaceRepository.save(buildWorkspace(owner, now)));

        ensureSettings(workspace, now);

        TagEntity positioning = ensureTag("tag-positioning", workspace, "定位", "positioning", now);
        TagEntity superWorkbench = ensureTag("tag-super-workbench", workspace, "超级个人工作台", "super-workbench", now);
        TagEntity agent = ensureTag("tag-agent", workspace, "Agent", "agent", now);
        TagEntity homepage = ensureTag("tag-homepage", workspace, "首页", "homepage", now);
        TagEntity systemDesign = ensureTag("tag-system-design", workspace, "系统设计", "system-design", now);
        TagEntity publicSurface = ensureTag("tag-public", workspace, "公共面", "public-surface", now);
        TagEntity blog = ensureTag("tag-blog", workspace, "博客", "blog", now);
        TagEntity authorPortal = ensureTag("tag-author-portal", workspace, "作者门户", "author-portal", now);

        ContentNodeEntity folderProduct = ensureFolder("folder-product-reframe", workspace, "产品重构", 100, now);
        ContentNodeEntity folderSystem = ensureFolder("folder-system-structure", workspace, "主系统结构", 200, now);
        ContentNodeEntity folderPublic = ensureFolder("folder-public-design", workspace, "公共面设计", 300, now);

        ensureNote(buildNote(
                "note-001",
                workspace,
                folderProduct,
                "把 Inkdesk 从知识库改造成超级个人工作台",
                110,
                Instant.parse("2026-04-12T08:10:00Z"),
                "重新定义公共面、主系统、Agent 控制台和任务计划在整个产品中的位置。",
                "# 把 Inkdesk 从知识库改造成超级个人工作台\n\n新的 Inkdesk 不再只是个人知识库加发布站，而是一个双面系统。\n\n这意味着主系统首页不该再只是最近笔记列表，而要成为帮助我判断、组织和推进工作的中枢。",
                1120,
                Set.of(positioning, superWorkbench, agent),
                buildPublication("pub-001", "super-personal-workbench-reframe", PublicationStatus.PUBLISHED, Instant.parse("2026-04-12T08:20:00Z"), Instant.parse("2026-04-12T08:20:00Z"))
        ));

        ensureNote(buildNote(
                "note-002",
                workspace,
                folderSystem,
                "为什么主系统首页必须先看到 Agent",
                210,
                Instant.parse("2026-04-12T07:42:00Z"),
                "记录 Agent 控制台为何要成为主人进入系统后的第一屏，而不是笔记列表或发布页。",
                "# 为什么主系统首页必须先看到 Agent\n\n如果首页先看到的只是文档列表，系统会退化成存储工具。\n\nAgent 首页的作用是把知识、任务和上下文重新编排。",
                860,
                Set.of(agent, homepage, systemDesign),
                buildPublication("pub-002", "why-agent-first", PublicationStatus.DRAFT, null, Instant.parse("2026-04-12T07:50:00Z"))
        ));

        ensureNote(buildNote(
                "note-003",
                workspace,
                folderPublic,
                "公共博客页作为作者门户的结构草案",
                310,
                Instant.parse("2026-04-12T06:58:00Z"),
                "公共面应该同时承载公开文章、作者介绍和长期项目入口，而不是产品官网式 landing page。",
                "# 公共博客页作为作者门户的结构草案\n\n公共面是别人理解作者与公开内容的入口，而不是进入私有系统的入口。",
                640,
                Set.of(publicSurface, blog, authorPortal),
                buildPublication("pub-003", "public-blog-author-portal", PublicationStatus.PUBLISHED, Instant.parse("2026-04-12T07:05:00Z"), Instant.parse("2026-04-12T07:05:00Z"))
        ));
    }

    private UserEntity buildOwner(Instant now) {
        UserEntity owner = new UserEntity();
        owner.setId("user-owner");
        owner.setUsername("owner");
        owner.setEmail("owner@inkdesk.local");
        owner.setPasswordHash("$2a$10$eV3G/Cflh.FS4xBtcOAxwOVImBnbvYWCUYaziOo05TGNBKLGQA6AK");
        owner.setStatus("ACTIVE");
        owner.setCreatedAt(now);
        owner.setUpdatedAt(now);
        return owner;
    }

    private WorkspaceEntity buildWorkspace(UserEntity owner, Instant now) {
        WorkspaceEntity workspace = new WorkspaceEntity();
        workspace.setId("workspace-inkdesk");
        workspace.setOwnerUser(owner);
        workspace.setName("Inkdesk");
        workspace.setSlug("inkdesk");
        workspace.setCreatedAt(now);
        workspace.setUpdatedAt(now);
        return workspace;
    }

    private void ensureSettings(WorkspaceEntity workspace, Instant now) {
        if (workspaceSettingsRepository.findById(workspace.getId()).isPresent()) {
            return;
        }

        WorkspaceSettingsEntity settings = new WorkspaceSettingsEntity();
        settings.setWorkspace(workspace);
        settings.setDisplayName("R");
        settings.setPublicTitle("构建超级个人工作台的人");
        settings.setSummary("我把 Inkdesk 当成自己的长期知识与执行系统，并持续向公共面输出成熟内容。");
        settings.setPublicLocation("Shanghai");
        settings.setDefaultPage("/app");
        settings.setCompactMode(false);
        settings.setShowContextRibbon(true);
        settings.setEditorDefaultView("edit");
        settings.setEditorAutoSave(true);
        settings.setEditorPublishReminder(true);
        settings.setPublishDefaultAudience("public");
        settings.setPublishShowProvenance(true);
        settings.setPublishHighlightRecentUpdates(true);
        settings.setCreatedAt(now);
        settings.setUpdatedAt(now);
        workspaceSettingsRepository.save(settings);
    }

    private TagEntity ensureTag(String id, WorkspaceEntity workspace, String name, String slug, Instant createdAt) {
        return tagRepository.findById(id)
                .orElseGet(() -> saveTag(id, workspace, name, slug, createdAt));
    }

    private TagEntity saveTag(String id, WorkspaceEntity workspace, String name, String slug, Instant createdAt) {
        TagEntity tag = new TagEntity();
        tag.setId(id);
        tag.setWorkspace(workspace);
        tag.setName(name);
        tag.setSlug(slug);
        tag.setCreatedAt(createdAt);
        return tagRepository.save(tag);
    }

    private ContentNodeEntity ensureFolder(String id, WorkspaceEntity workspace, String title, int sortOrder, Instant updatedAt) {
        return contentNodeRepository.findById(id)
                .orElseGet(() -> saveFolder(id, workspace, title, sortOrder, updatedAt));
    }

    private ContentNodeEntity saveFolder(String id, WorkspaceEntity workspace, String title, int sortOrder, Instant updatedAt) {
        ContentNodeEntity folder = new ContentNodeEntity();
        folder.setId(id);
        folder.setWorkspace(workspace);
        folder.setType(NodeType.FOLDER);
        folder.setTitle(title);
        folder.setSortOrder(sortOrder);
        folder.setStatus("ACTIVE");
        folder.setCreatedAt(updatedAt);
        folder.setUpdatedAt(updatedAt);
        return contentNodeRepository.save(folder);
    }

    private void ensureNote(ContentNodeEntity note) {
        if (contentNodeRepository.findNoteByIdWithRelations(note.getId()).isPresent()) {
            return;
        }

        contentNodeRepository.save(note);
    }

    private ContentNodeEntity buildNote(
            String id,
            WorkspaceEntity workspace,
            ContentNodeEntity parent,
            String title,
            int sortOrder,
            Instant updatedAt,
            String excerpt,
            String markdown,
            int wordCount,
            Set<TagEntity> tags,
            PublicationEntity publication
    ) {
        ContentNodeEntity note = new ContentNodeEntity();
        note.setId(id);
        note.setWorkspace(workspace);
        note.setParent(parent);
        note.setType(NodeType.NOTE);
        note.setTitle(title);
        note.setSortOrder(sortOrder);
        note.setStatus("ACTIVE");
        note.setCreatedAt(updatedAt);
        note.setUpdatedAt(updatedAt);
        note.setTags(new LinkedHashSet<>(tags));

        NoteDocumentEntity document = new NoteDocumentEntity();
        document.setId(id.replace("note", "doc"));
        document.setNote(note);
        document.setExcerpt(excerpt);
        document.setMarkdownContent(markdown);
        document.setWordCount(wordCount);
        document.setUpdatedAt(updatedAt);
        note.setNoteDocument(document);

        publication.setNote(note);
        note.setPublication(publication);

        return note;
    }

    private PublicationEntity buildPublication(
            String id,
            String slug,
            PublicationStatus status,
            Instant publishedAt,
            Instant updatedAt
    ) {
        PublicationEntity publication = new PublicationEntity();
        publication.setId(id);
        publication.setSlug(slug);
        publication.setStatus(status);
        publication.setPublishedAt(publishedAt);
        publication.setUpdatedAt(updatedAt);
        return publication;
    }
}
