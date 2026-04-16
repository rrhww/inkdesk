package com.inkdesk.server.home;

public record AdminHomeQuickActionResponse(
        String id,
        String label,
        String summary,
        String href,
        String icon
) {
}
