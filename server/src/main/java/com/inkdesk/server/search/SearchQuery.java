package com.inkdesk.server.search;

public record SearchQuery(
        String q,
        String visibility,
        String tag,
        String folder
) {
}
