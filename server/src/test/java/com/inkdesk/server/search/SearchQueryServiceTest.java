package com.inkdesk.server.search;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class SearchQueryServiceTest {

    @Autowired(required = false)
    private SearchQueryService searchQueryService;

    @Test
    void scoresTitleAndTagHitsAheadOfExcerptHits() {
        assertThat(searchQueryService).isNotNull();

        var results = searchQueryService.searchKnowledge(new SearchQuery("agent", null, null, null));

        assertThat(results).hasSize(2);
        assertThat(results.get(0).note().id()).isEqualTo("note-002");
        assertThat(results.get(0).score()).isGreaterThan(results.get(1).score());
    }

    @Test
    void filtersByFolderWithoutThrowingWhenPublicationIsMissing() {
        assertThat(searchQueryService).isNotNull();

        var results = searchQueryService.searchKnowledge(new SearchQuery("公共", "public", "公共面", "公共面设计"));

        assertThat(results)
                .singleElement()
                .extracting(result -> result.note().id())
                .isEqualTo("note-003");
    }
}
