package com.inkdesk.server.knowledge.api;

import java.time.Instant;
import java.util.List;

public record AdminNoteDetailResponse(
        String id,
        String parentId,
        String title,
        String excerpt,
        String markdownContent,
        Instant updatedAt,
        List<String> tags,
        String visibility,
        boolean published,
        String slug
) {
}
