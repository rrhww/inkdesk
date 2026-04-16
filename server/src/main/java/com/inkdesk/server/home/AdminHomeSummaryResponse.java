package com.inkdesk.server.home;

public record AdminHomeSummaryResponse(
        int activePlans,
        int privateNotes,
        int publishedNotes,
        int linkedNotes
) {
}
