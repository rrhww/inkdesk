package com.inkdesk.server.home;

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
@Sql(
        scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql", "/testdata/plans-fixtures.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD
)
class HomeApiIntegrationTest {

    private static final String OWNER_COOKIE = "inkdesk_owner_session=owner";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void requiresOwnerCookieForHomeSnapshot() throws Exception {
        mockMvc.perform(get("/api/admin/home"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void returnsAggregatedHomeSnapshotForOwner() throws Exception {
        mockMvc.perform(get("/api/admin/home").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.activePlans").value(2))
                .andExpect(jsonPath("$.summary.privateNotes").value(1))
                .andExpect(jsonPath("$.summary.publishedNotes").value(2))
                .andExpect(jsonPath("$.summary.linkedNotes").value(3))
                .andExpect(jsonPath("$.focusPlan.id").value("plan-001"))
                .andExpect(jsonPath("$.focusPlan.searchTerm").value("公共面"))
                .andExpect(jsonPath("$.focusNote.id").value("note-002"))
                .andExpect(jsonPath("$.recentKnowledge.length()").value(3))
                .andExpect(jsonPath("$.recentKnowledge[0].id").value("note-001"))
                .andExpect(jsonPath("$.recentKnowledge[1].id").value("note-002"))
                .andExpect(jsonPath("$.recentKnowledge[2].id").value("note-003"))
                .andExpect(jsonPath("$.publishQueue.length()").value(1))
                .andExpect(jsonPath("$.publishQueue[0].noteId").value("note-002"))
                .andExpect(jsonPath("$.suggestions.length()").value(3))
                .andExpect(jsonPath("$.quickActions.length()").value(4));
    }
}
