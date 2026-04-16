package com.inkdesk.server.plans;

import java.util.List;

public record PlanUpsertRequest(
        String title,
        String summary,
        String status,
        String horizon,
        String priority,
        String focusLabel,
        String nextStep,
        String nextActionLabel,
        String nextActionHref,
        String searchTerm,
        String agentPrompt,
        List<String> relatedNoteIds
) {
}
