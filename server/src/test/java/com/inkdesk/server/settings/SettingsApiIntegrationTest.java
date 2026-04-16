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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class SettingsApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void returnsPersistedWorkspaceSettingsForAuthenticatedOwner() throws Exception {
        String sessionToken = loginAndReturnToken();

        mockMvc.perform(get("/api/admin/settings").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.profile.displayName").value("R"))
                .andExpect(jsonPath("$.workbench.defaultPage").value("/app"))
                .andExpect(jsonPath("$.editor.defaultView").value("edit"))
                .andExpect(jsonPath("$.publish.defaultAudience").value("public"))
                .andExpect(jsonPath("$.security.ownerEmail").value("owner@inkdesk.local"));
    }

    @Test
    void updatesWorkspaceSettingsAndKeepsSecurityFieldsReadOnly() throws Exception {
        String sessionToken = loginAndReturnToken();

        mockMvc.perform(patch("/api/admin/settings")
                        .header("Cookie", sessionCookie(sessionToken))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "profile": {
                                    "displayName": "Inkdesk Owner",
                                    "publicTitle": "本地闭环实验者",
                                    "summary": "更新后的摘要",
                                    "publicLocation": "Shanghai"
                                  },
                                  "workbench": {
                                    "defaultPage": "/app/plans",
                                    "compactMode": true,
                                    "showContextRibbon": false
                                  },
                                  "editor": {
                                    "defaultView": "preview",
                                    "autoSave": false,
                                    "publishReminder": false
                                  },
                                  "publish": {
                                    "defaultAudience": "private",
                                    "showProvenance": false,
                                    "highlightRecentUpdates": false
                                  },
                                  "security": {
                                    "ownerEmail": "attacker@example.com",
                                    "sessionMode": "公开入口",
                                    "sessionDurationLabel": "1 分钟"
                                  }
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.profile.displayName").value("Inkdesk Owner"))
                .andExpect(jsonPath("$.workbench.defaultPage").value("/app/plans"))
                .andExpect(jsonPath("$.editor.defaultView").value("preview"))
                .andExpect(jsonPath("$.publish.defaultAudience").value("private"))
                .andExpect(jsonPath("$.security.ownerEmail").value("owner@inkdesk.local"))
                .andExpect(jsonPath("$.security.sessionMode").value("隐藏主人入口"));

        mockMvc.perform(get("/api/admin/settings").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.profile.displayName").value("Inkdesk Owner"))
                .andExpect(jsonPath("$.profile.publicTitle").value("本地闭环实验者"))
                .andExpect(jsonPath("$.profile.summary").value("更新后的摘要"))
                .andExpect(jsonPath("$.workbench.defaultPage").value("/app/plans"))
                .andExpect(jsonPath("$.workbench.compactMode").value(true))
                .andExpect(jsonPath("$.editor.autoSave").value(false))
                .andExpect(jsonPath("$.publish.showProvenance").value(false))
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
