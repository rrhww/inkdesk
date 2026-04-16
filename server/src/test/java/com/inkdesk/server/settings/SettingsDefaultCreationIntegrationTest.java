package com.inkdesk.server.settings;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/owner-without-settings.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class SettingsDefaultCreationIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void createsDefaultWorkspaceSettingsWhenMissing() throws Exception {
        String sessionToken = loginAndReturnToken();

        mockMvc.perform(get("/api/admin/settings").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.profile.displayName").value("R"))
                .andExpect(jsonPath("$.profile.publicTitle").value("构建超级个人工作台的人"))
                .andExpect(jsonPath("$.workbench.defaultPage").value("/app"))
                .andExpect(jsonPath("$.publish.defaultAudience").value("public"))
                .andExpect(jsonPath("$.security.ownerEmail").value("owner@inkdesk.local"));
    }

    private String loginAndReturnToken() throws Exception {
        String body = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "email": "owner@inkdesk.local",
                                  "password": "inkdesk-owner"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionToken").isString())
                .andReturn()
                .getResponse()
                .getContentAsString();

        JsonNode payload = objectMapper.readTree(body);
        return payload.get("sessionToken").asText();
    }

    private String sessionCookie(String sessionToken) {
        return "inkdesk_owner_session=" + sessionToken;
    }
}
