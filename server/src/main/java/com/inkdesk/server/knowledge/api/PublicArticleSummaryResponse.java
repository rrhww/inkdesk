package com.inkdesk.server.knowledge.api;

import java.time.Instant;
import java.util.List;

public record PublicArticleSummaryResponse(
        String id,
        String title,
        String excerpt,
        String slug,
        Instant updatedAt,
        List<String> tags
) {
}
