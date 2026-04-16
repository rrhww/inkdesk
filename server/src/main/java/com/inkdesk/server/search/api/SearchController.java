package com.inkdesk.server.search.api;

import com.inkdesk.server.search.SearchQuery;
import com.inkdesk.server.search.SearchQueryService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/admin/search")
public class SearchController {

    private final SearchQueryService searchQueryService;

    public SearchController(SearchQueryService searchQueryService) {
        this.searchQueryService = searchQueryService;
    }

    @GetMapping
    public List<AdminSearchResultResponse> searchKnowledge(
            @RequestParam String q,
            @RequestParam(required = false) String visibility,
            @RequestParam(required = false) String tag,
            @RequestParam(required = false) String folder
    ) {
        return searchQueryService.searchKnowledge(new SearchQuery(q, visibility, tag, folder));
    }
}
