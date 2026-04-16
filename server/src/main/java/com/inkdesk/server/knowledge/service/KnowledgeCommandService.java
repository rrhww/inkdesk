package com.inkdesk.server.knowledge.service;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import com.inkdesk.server.knowledge.api.AdminNoteDetailResponse;
import com.inkdesk.server.knowledge.api.NoteUpsertRequest;
import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.NoteDocumentEntity;
import com.inkdesk.server.knowledge.persistence.PublicationEntity;
import com.inkdesk.server.knowledge.persistence.PublicationRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.text.Normalizer;
import java.time.Instant;
import java.util.Locale;
import java.util.UUID;

@Service
public class KnowledgeCommandService {

    private static final String DEFAULT_WORKSPACE_SLUG = "inkdesk";

    private final ContentNodeRepository contentNodeRepository;
    private final WorkspaceRepository workspaceRepository;
    private final PublicationRepository publicationRepository;
    private final KnowledgeQueryService knowledgeQueryService;

    public KnowledgeCommandService(
            ContentNodeRepository contentNodeRepository,
            WorkspaceRepository workspaceRepository,
            PublicationRepository publicationRepository,
            KnowledgeQueryService knowledgeQueryService
    ) {
        this.contentNodeRepository = contentNodeRepository;
        this.workspaceRepository = workspaceRepository;
        this.publicationRepository = publicationRepository;
        this.knowledgeQueryService = knowledgeQueryService;
    }

    @Transactional
    public AdminNoteDetailResponse createNote(NoteUpsertRequest request) {
        WorkspaceEntity workspace = workspaceRepository.findBySlug(DEFAULT_WORKSPACE_SLUG)
                .orElseThrow(() -> new ResourceNotFoundException("Workspace not found: " + DEFAULT_WORKSPACE_SLUG));
        ContentNodeEntity parent = resolveParent(request.parentId());
        Instant now = Instant.now();

        ContentNodeEntity note = new ContentNodeEntity();
        note.setId(nextId("note"));
        note.setWorkspace(workspace);
        note.setParent(parent);
        note.setType(NodeType.NOTE);
        note.setTitle(normalizeRequired(request.title(), "title"));
        note.setSortOrder(nextSortOrder(workspace.getId(), parent));
        note.setStatus("ACTIVE");
        note.setCreatedAt(now);
        note.setUpdatedAt(now);
        note.setNoteDocument(buildDocument(note, request, now));

        contentNodeRepository.save(note);
        return knowledgeQueryService.getAdminNoteDetail(note.getId());
    }

    @Transactional
    public AdminNoteDetailResponse updateNote(String noteId, NoteUpsertRequest request) {
        ContentNodeEntity note = contentNodeRepository.findNoteByIdWithRelations(noteId)
                .orElseThrow(() -> new ResourceNotFoundException("Knowledge asset not found: " + noteId));
        Instant now = Instant.now();
        ContentNodeEntity parent = resolveParent(request.parentId());

        if (parent == null && note.getParent() != null || parent != null && (note.getParent() == null || !parent.getId().equals(note.getParent().getId()))) {
            note.setParent(parent);
            note.setSortOrder(nextSortOrder(note.getWorkspace().getId(), parent));
        }

        note.setTitle(normalizeRequired(request.title(), "title"));
        note.setUpdatedAt(now);

        NoteDocumentEntity document = note.getNoteDocument();
        if (document == null) {
            document = buildDocument(note, request, now);
            note.setNoteDocument(document);
        } else {
            document.setExcerpt(normalizeOptional(request.excerpt()));
            document.setMarkdownContent(normalizeMarkdown(request.markdownContent()));
            document.setWordCount(countWords(document.getMarkdownContent()));
            document.setUpdatedAt(now);
        }

        contentNodeRepository.save(note);
        return knowledgeQueryService.getAdminNoteDetail(note.getId());
    }

    @Transactional
    public AdminNoteDetailResponse publishNote(String noteId) {
        ContentNodeEntity note = contentNodeRepository.findNoteByIdWithRelations(noteId)
                .orElseThrow(() -> new ResourceNotFoundException("Knowledge asset not found: " + noteId));
        Instant now = Instant.now();
        PublicationEntity publication = note.getPublication();

        if (publication == null) {
            publication = new PublicationEntity();
            publication.setId(nextId("pub"));
            publication.setNote(note);
            publication.setSlug(generateUniqueSlug(note.getTitle()));
            note.setPublication(publication);
        }

        publication.setStatus(PublicationStatus.PUBLISHED);
        publication.setPublishedAt(now);
        publication.setUpdatedAt(now);
        note.setUpdatedAt(now);

        contentNodeRepository.save(note);
        return knowledgeQueryService.getAdminNoteDetail(note.getId());
    }

    @Transactional
    public AdminNoteDetailResponse unpublishNote(String noteId) {
        ContentNodeEntity note = contentNodeRepository.findNoteByIdWithRelations(noteId)
                .orElseThrow(() -> new ResourceNotFoundException("Knowledge asset not found: " + noteId));
        PublicationEntity publication = note.getPublication();

        if (publication == null) {
            throw new ResourceNotFoundException("Publication not found for knowledge asset: " + noteId);
        }

        Instant now = Instant.now();
        publication.setStatus(PublicationStatus.DRAFT);
        publication.setUpdatedAt(now);
        note.setUpdatedAt(now);

        contentNodeRepository.save(note);
        return knowledgeQueryService.getAdminNoteDetail(note.getId());
    }

    private ContentNodeEntity resolveParent(String parentId) {
        if (parentId == null || parentId.isBlank()) {
            return null;
        }

        return contentNodeRepository.findByIdAndTypeWithRelations(parentId, NodeType.FOLDER)
                .orElseThrow(() -> new ResourceNotFoundException("Parent folder not found: " + parentId));
    }

    private NoteDocumentEntity buildDocument(ContentNodeEntity note, NoteUpsertRequest request, Instant now) {
        NoteDocumentEntity document = new NoteDocumentEntity();
        document.setId(nextId("doc"));
        document.setNote(note);
        document.setExcerpt(normalizeOptional(request.excerpt()));
        document.setMarkdownContent(normalizeMarkdown(request.markdownContent()));
        document.setWordCount(countWords(document.getMarkdownContent()));
        document.setUpdatedAt(now);
        return document;
    }

    private int nextSortOrder(String workspaceId, ContentNodeEntity parent) {
        Integer currentMax = contentNodeRepository.findMaxSortOrderByWorkspaceAndParentId(
                workspaceId,
                parent != null ? parent.getId() : null
        );
        return (currentMax == null ? 0 : currentMax) + 10;
    }

    private String generateUniqueSlug(String title) {
        String base = slugify(title);

        if (!publicationRepository.existsBySlug(base)) {
            return base;
        }

        int suffix = 2;
        while (true) {
            String candidate = appendSlugSuffix(base, suffix);
            if (!publicationRepository.existsBySlug(candidate)) {
                return candidate;
            }
            suffix++;
        }
    }

    private String slugify(String value) {
        String normalized = Normalizer.normalize(normalizeRequired(value, "title"), Normalizer.Form.NFKC)
                .toLowerCase(Locale.ROOT)
                .replaceAll("[^\\p{L}\\p{Nd}]+", "-")
                .replaceAll("^-+", "")
                .replaceAll("-+$", "")
                .replaceAll("-{2,}", "-");

        if (!normalized.isBlank()) {
            return truncateSlug(normalized, 160);
        }

        return "note-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }

    private String appendSlugSuffix(String base, int suffix) {
        String suffixValue = "-" + suffix;
        int maxBaseLength = Math.max(1, 160 - suffixValue.length());
        return truncateSlug(base, maxBaseLength) + suffixValue;
    }

    private String truncateSlug(String value, int maxLength) {
        if (value.length() <= maxLength) {
            return value;
        }

        return value.substring(0, maxLength).replaceAll("-+$", "");
    }

    private String normalizeRequired(String value, String fieldName) {
        String normalized = value == null ? "" : value.trim();

        if (normalized.isEmpty()) {
            throw new IllegalArgumentException("Missing required field: " + fieldName);
        }

        return normalized;
    }

    private String normalizeOptional(String value) {
        if (value == null) {
            return null;
        }

        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private String normalizeMarkdown(String markdownContent) {
        return markdownContent == null ? "" : markdownContent.trim();
    }

    private int countWords(String markdownContent) {
        String plainText = markdownContent
                .replaceAll("[#>*`~\\-]", " ")
                .replaceAll("\\s+", " ")
                .trim();

        if (plainText.isEmpty()) {
            return 0;
        }

        return plainText.split(" ").length;
    }

    private String nextId(String prefix) {
        return prefix + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }
}
