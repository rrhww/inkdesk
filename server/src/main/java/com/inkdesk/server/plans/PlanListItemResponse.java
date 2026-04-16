package com.inkdesk.server.plans;

import java.time.Instant;
import java.util.List;

public record PlanListItemResponse(
        String id,
        String title,
        String summary,
        String status,
        String statusLabel,
        String horizon,
        String horizonLabel,
        String priority,
        String priorityLabel,
        String focusLabel,
        String nextStep,
        String nextActionLabel,
        String nextActionHref,
        String searchTerm,
        String agentPrompt,
        Instant updatedAt,
        List<String> relatedNoteIds
) {
}
