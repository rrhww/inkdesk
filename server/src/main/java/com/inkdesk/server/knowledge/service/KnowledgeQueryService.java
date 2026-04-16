package com.inkdesk.server.knowledge.service;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import com.inkdesk.server.knowledge.api.AdminNoteDetailResponse;
import com.inkdesk.server.knowledge.api.AdminNoteTreeItemResponse;
import com.inkdesk.server.knowledge.api.PublicArticleDetailResponse;
import com.inkdesk.server.knowledge.api.PublicArticleSummaryResponse;
import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Comparator;
import java.util.List;

@Service
public class KnowledgeQueryService {

    private static final String DEFAULT_WORKSPACE_SLUG = "inkdesk";

    private final ContentNodeRepository contentNodeRepository;

    public KnowledgeQueryService(ContentNodeRepository contentNodeRepository) {
        this.contentNodeRepository = contentNodeRepository;
    }

    @Transactional(readOnly = true)
    public List<AdminNoteTreeItemResponse> getAdminNoteTree() {
        return contentNodeRepository.findTreeByWorkspaceSlugWithRelations(DEFAULT_WORKSPACE_SLUG).stream()
                .sorted(adminTreeComparator())
                .map(this::toAdminTreeItem)
                .toList();
    }

    @Transactional(readOnly = true)
    public AdminNoteDetailResponse getAdminNoteDetail(String noteId) {
        ContentNodeEntity note = contentNodeRepository.findNoteByIdWithRelations(noteId)
                .orElseThrow(() -> new ResourceNotFoundException("Knowledge asset not found: " + noteId));

        return new AdminNoteDetailResponse(
                note.getId(),
                note.getParent() != null ? note.getParent().getId() : null,
                note.getTitle(),
                note.getNoteDocument() != null ? note.getNoteDocument().getExcerpt() : null,
                note.getNoteDocument() != null ? note.getNoteDocument().getMarkdownContent() : "",
                resolveUpdatedAt(note),
                note.getTags().stream().map(Tag -> Tag.getName()).sorted().toList(),
                resolveVisibility(note),
                isPublished(note),
                note.getPublication() != null ? note.getPublication().getSlug() : null
        );
    }

    @Transactional(readOnly = true)
    public List<PublicArticleSummaryResponse> getPublicArticles() {
        return contentNodeRepository.findAllByPublicationStatusWithRelations(PublicationStatus.PUBLISHED).stream()
                .sorted(Comparator.comparing(this::resolveUpdatedAt).reversed())
                .map(this::toPublicArticleSummary)
                .toList();
    }

    @Transactional(readOnly = true)
    public PublicArticleDetailResponse getPublicArticle(String slug) {
        ContentNodeEntity note = contentNodeRepository.findByPublicationSlugAndStatusWithRelations(slug, PublicationStatus.PUBLISHED)
                .orElseThrow(() -> new ResourceNotFoundException("Public article not found: " + slug));

        return new PublicArticleDetailResponse(
                note.getId(),
                note.getTitle(),
                note.getNoteDocument() != null ? note.getNoteDocument().getExcerpt() : null,
                note.getPublication().getSlug(),
                note.getNoteDocument() != null ? note.getNoteDocument().getMarkdownContent() : "",
                resolveUpdatedAt(note),
                note.getTags().stream().map(tag -> tag.getName()).sorted().toList()
        );
    }

    private AdminNoteTreeItemResponse toAdminTreeItem(ContentNodeEntity node) {
        return new AdminNoteTreeItemResponse(
                node.getId(),
                node.getParent() != null ? node.getParent().getId() : null,
                node.getType().name().toLowerCase(),
                node.getTitle(),
                node.getSortOrder(),
                resolveUpdatedAt(node),
                node.getNoteDocument() != null ? node.getNoteDocument().getExcerpt() : null,
                node.getTags().stream().map(tag -> tag.getName()).sorted().toList(),
                resolveVisibility(node),
                isPublished(node),
                node.getPublication() != null ? node.getPublication().getSlug() : null
        );
    }

    private PublicArticleSummaryResponse toPublicArticleSummary(ContentNodeEntity node) {
        return new PublicArticleSummaryResponse(
                node.getId(),
                node.getTitle(),
                node.getNoteDocument() != null ? node.getNoteDocument().getExcerpt() : null,
                node.getPublication().getSlug(),
                resolveUpdatedAt(node),
                node.getTags().stream().map(tag -> tag.getName()).sorted().toList()
        );
    }

    private Comparator<ContentNodeEntity> adminTreeComparator() {
        return Comparator
                .comparing((ContentNodeEntity node) -> node.getParent() == null ? 0 : 1)
                .thenComparing(node -> node.getParent() == null ? node.getSortOrder() : node.getParent().getSortOrder())
                .thenComparing(ContentNodeEntity::getSortOrder)
                .thenComparing(ContentNodeEntity::getTitle);
    }

    private Instant resolveUpdatedAt(ContentNodeEntity node) {
        if (node.getType() == NodeType.NOTE && node.getNoteDocument() != null) {
            return node.getNoteDocument().getUpdatedAt();
        }

        return node.getUpdatedAt();
    }

    private boolean isPublished(ContentNodeEntity node) {
        return node.getPublication() != null && node.getPublication().getStatus() == PublicationStatus.PUBLISHED;
    }

    private String resolveVisibility(ContentNodeEntity node) {
        return isPublished(node) ? "public" : "private";
    }
}
