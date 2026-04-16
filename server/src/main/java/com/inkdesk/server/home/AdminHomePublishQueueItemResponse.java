package com.inkdesk.server.home;

import java.time.Instant;

public record AdminHomePublishQueueItemResponse(
        String noteId,
        String title,
        String excerpt,
        Instant updatedAt,
        String state,
        String stateLabel
) {
}
