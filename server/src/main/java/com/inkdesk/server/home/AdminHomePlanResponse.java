package com.inkdesk.server.home;

public record AdminHomePlanResponse(
        String id,
        String title,
        String statusLabel,
        String horizonLabel,
        String priorityLabel,
        String nextStep,
        String nextActionLabel,
        String nextActionHref,
        String searchTerm
) {
}
