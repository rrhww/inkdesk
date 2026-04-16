package com.inkdesk.server.search.api;

import java.time.Instant;
import java.util.List;

public record AdminSearchNoteResponse(
        String id,
        String title,
        String excerpt,
        List<String> tags,
        String folder,
        Instant updatedAt,
        String visibility,
        boolean published,
        String slug
) {
}
