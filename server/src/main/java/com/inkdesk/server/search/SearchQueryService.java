package com.inkdesk.server.search;

import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.search.api.AdminSearchNoteResponse;
import com.inkdesk.server.search.api.AdminSearchResultResponse;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

@Service
public class SearchQueryService {

    private static final String DEFAULT_WORKSPACE_SLUG = "inkdesk";

    private final ContentNodeRepository contentNodeRepository;

    public SearchQueryService(ContentNodeRepository contentNodeRepository) {
        this.contentNodeRepository = contentNodeRepository;
    }

    @Transactional(readOnly = true)
    public List<AdminSearchResultResponse> searchKnowledge(SearchQuery query) {
        String normalizedQuery = normalize(query.q());

        if (normalizedQuery.isBlank()) {
            return List.of();
        }

        return contentNodeRepository.findTreeByWorkspaceSlugWithRelations(DEFAULT_WORKSPACE_SLUG).stream()
                .filter(node -> node.getType() == NodeType.NOTE)
                .map(node -> scoreNode(node, query, normalizedQuery))
                .filter(Objects::nonNull)
                .sorted(Comparator
                        .comparingInt(AdminSearchResultResponse::score)
                        .reversed()
                        .thenComparing(result -> result.note().updatedAt(), Comparator.reverseOrder()))
                .toList();
    }

    private AdminSearchResultResponse scoreNode(ContentNodeEntity node, SearchQuery query, String normalizedQuery) {
        String folder = node.getParent() != null ? node.getParent().getTitle() : "";
        String visibility = resolveVisibility(node);

        if (!matchesVisibility(visibility, query.visibility())) {
            return null;
        }

        if (!matchesTag(node, query.tag())) {
            return null;
        }

        if (!matchesFolder(folder, query.folder())) {
            return null;
        }

        List<String> hitLabels = new ArrayList<>();
        List<String> matchedTerms = new ArrayList<>();
        int score = 0;

        if (contains(node.getTitle(), normalizedQuery)) {
            score += 6;
            hitLabels.add("标题");
            matchedTerms.add(node.getTitle());
        }

        List<String> matchedTags = node.getTags().stream()
                .map(tag -> tag.getName())
                .filter(tag -> contains(tag, normalizedQuery))
                .toList();
        if (!matchedTags.isEmpty()) {
            score += 5;
            hitLabels.add("标签");
            matchedTerms.addAll(matchedTags);
        }

        String excerpt = node.getNoteDocument() != null ? node.getNoteDocument().getExcerpt() : "";
        if (contains(excerpt, normalizedQuery)) {
            score += 4;
            hitLabels.add("摘要");
            matchedTerms.add(excerpt);
        }

        if (contains(folder, normalizedQuery)) {
            score += 3;
            hitLabels.add("文件夹");
            matchedTerms.add(folder);
        }

        String markdown = node.getNoteDocument() != null ? node.getNoteDocument().getMarkdownContent() : "";
        if (contains(markdown, normalizedQuery)) {
            score += 2;
            hitLabels.add("正文");
            matchedTerms.add(markdown);
        }

        if (score == 0) {
            return null;
        }

        return new AdminSearchResultResponse(
                new AdminSearchNoteResponse(
                        node.getId(),
                        node.getTitle(),
                        excerpt,
                        node.getTags().stream().map(tag -> tag.getName()).sorted().toList(),
                        folder,
                        resolveUpdatedAt(node),
                        visibility,
                        isPublished(node),
                        node.getPublication() != null ? node.getPublication().getSlug() : null
                ),
                score,
                new ArrayList<>(new LinkedHashSet<>(hitLabels)),
                matchedTerms.stream().filter(term -> term != null && !term.isBlank()).toList()
        );
    }

    private boolean matchesVisibility(String visibility, String requestedVisibility) {
        String normalizedVisibility = normalize(requestedVisibility);
        return normalizedVisibility.isBlank() || "all".equals(normalizedVisibility) || visibility.equals(normalizedVisibility);
    }

    private boolean matchesTag(ContentNodeEntity node, String requestedTag) {
        String normalizedTag = normalize(requestedTag);
        if (normalizedTag.isBlank()) {
            return true;
        }

        return node.getTags().stream()
                .map(tag -> normalize(tag.getName()))
                .anyMatch(normalizedTag::equals);
    }

    private boolean matchesFolder(String folder, String requestedFolder) {
        String normalizedFolder = normalize(requestedFolder);
        return normalizedFolder.isBlank() || normalize(folder).equals(normalizedFolder);
    }

    private boolean contains(String value, String normalizedQuery) {
        return normalize(value).contains(normalizedQuery);
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
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
