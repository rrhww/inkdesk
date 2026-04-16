package com.inkdesk.server.search.api;

import java.util.List;

public record AdminSearchResultResponse(
        AdminSearchNoteResponse note,
        int score,
        List<String> hitLabels,
        List<String> matchedTerms
) {
}
