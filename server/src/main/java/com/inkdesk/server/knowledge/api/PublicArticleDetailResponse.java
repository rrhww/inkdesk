package com.inkdesk.server.knowledge.api;

import java.time.Instant;
import java.util.List;

public record PublicArticleDetailResponse(
        String id,
        String title,
        String excerpt,
        String slug,
        String markdownContent,
        Instant updatedAt,
        List<String> tags
) {
}
