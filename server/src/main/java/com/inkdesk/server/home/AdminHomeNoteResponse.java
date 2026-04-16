package com.inkdesk.server.home;

import java.time.Instant;

public record AdminHomeNoteResponse(
        String id,
        String title,
        String excerpt,
        String folder,
        Instant updatedAt,
        boolean published,
        String visibility,
        String visibilityLabel
) {
}
