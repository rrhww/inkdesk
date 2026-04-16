package com.inkdesk.server.search;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class SearchApiIntegrationTest {

    private static final String OWNER_COOKIE = "inkdesk_owner_session=owner";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void returnsRankedKnowledgeHitsForQuery() throws Exception {
        mockMvc.perform(get("/api/admin/search")
                        .param("q", "Agent")
                        .header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].note.id").value("note-002"))
                .andExpect(jsonPath("$[0].hitLabels").isArray())
                .andExpect(jsonPath("$[0].hitLabels[0]").exists());
    }

    @Test
    void appliesVisibilityTagAndFolderFilters() throws Exception {
        mockMvc.perform(get("/api/admin/search")
                        .param("q", "公共")
                        .param("visibility", "public")
                        .param("tag", "公共面")
                        .param("folder", "公共面设计")
                        .header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].note.id").value("note-003"));
    }

    @Test
    void returnsEmptyListForBlankQuery() throws Exception {
        mockMvc.perform(get("/api/admin/search")
                        .param("q", "   ")
                        .header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }
}
