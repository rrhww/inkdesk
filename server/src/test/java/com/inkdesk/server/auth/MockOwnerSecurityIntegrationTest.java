package com.inkdesk.server.auth;

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
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class MockOwnerSecurityIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void rejectsUnauthenticatedRequestsToPrivateEndpoints() throws Exception {
        mockMvc.perform(get("/api/auth/me"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));

        mockMvc.perform(get("/api/admin/notes/tree"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }

    @Test
    void loginIssuesSessionTokenAndAllowsPrivateRequests() throws Exception {
        String sessionToken = loginAndReturnToken("owner@inkdesk.local", "inkdesk-owner");

        mockMvc.perform(get("/api/auth/me").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("owner"))
                .andExpect(jsonPath("$.workspaceSlug").value("inkdesk"));

        mockMvc.perform(get("/api/admin/notes/tree").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.id=='note-001')]").exists());
    }

    @Test
    void rejectsInvalidCredentialsForLogin() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "email": "owner@inkdesk.local",
                                  "password": "wrong-password"
                                }
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void logoutInvalidatesPreviouslyIssuedSessionToken() throws Exception {
        String sessionToken = loginAndReturnToken("owner@inkdesk.local", "inkdesk-owner");

        mockMvc.perform(post("/api/auth/logout").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/api/auth/me").header("Cookie", sessionCookie(sessionToken)))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }

    private String loginAndReturnToken(String email, String password) throws Exception {
        String body = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "email": "%s",
                                  "password": "%s"
                                }
                                """.formatted(email, password)))
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
