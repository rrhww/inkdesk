package com.inkdesk.server.home;

public record AdminHomeSuggestionResponse(
        String id,
        String category,
        String title,
        String summary,
        String actionLabel,
        String href
) {
}
