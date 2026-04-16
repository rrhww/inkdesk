package com.inkdesk.server.knowledge.api;

public record NoteUpsertRequest(
        String title,
        String parentId,
        String excerpt,
        String markdownContent
) {
}
