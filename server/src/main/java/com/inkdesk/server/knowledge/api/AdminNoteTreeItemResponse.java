package com.inkdesk.server.knowledge.api;

import java.time.Instant;
import java.util.List;

public record AdminNoteTreeItemResponse(
        String id,
        String parentId,
        String type,
        String title,
        Integer sortOrder,
        Instant updatedAt,
        String excerpt,
        List<String> tags,
        String visibility,
        boolean published,
        String slug
) {
}
