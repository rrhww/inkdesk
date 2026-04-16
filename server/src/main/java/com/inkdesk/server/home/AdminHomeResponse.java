package com.inkdesk.server.home;

import java.util.List;

public record AdminHomeResponse(
        AdminHomeSummaryResponse summary,
        AdminHomePlanResponse focusPlan,
        AdminHomeNoteResponse focusNote,
        List<AdminHomeSuggestionResponse> suggestions,
        List<AdminHomeQuickActionResponse> quickActions,
        List<AdminHomeNoteResponse> recentKnowledge,
        List<AdminHomePublishQueueItemResponse> publishQueue
) {
}
