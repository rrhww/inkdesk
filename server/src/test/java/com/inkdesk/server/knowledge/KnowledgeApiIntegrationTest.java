package com.inkdesk.server.knowledge;

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
class KnowledgeApiIntegrationTest {

    private static final String OWNER_COOKIE = "inkdesk_owner_session=owner";

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void returnsAdminNoteTreeWithFoldersAndNotes() throws Exception {
        mockMvc.perform(get("/api/admin/notes/tree").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].type").value("folder"))
                .andExpect(jsonPath("$[?(@.id=='folder-product-reframe')]").exists())
                .andExpect(jsonPath("$[?(@.id=='note-001')].published").value(true))
                .andExpect(jsonPath("$[?(@.id=='note-002')].visibility").value("private"));
    }

    @Test
    void returnsAdminNoteDetailWithMarkdownAndPublicationState() throws Exception {
        mockMvc.perform(get("/api/admin/notes/note-001").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value("note-001"))
                .andExpect(jsonPath("$.slug").value("super-personal-workbench-reframe"))
                .andExpect(jsonPath("$.published").value(true))
                .andExpect(jsonPath("$.markdownContent").value(org.hamcrest.Matchers.containsString("超级个人工作台")));
    }

    @Test
    void returnsNotFoundForMissingAdminNote() throws Exception {
        mockMvc.perform(get("/api/admin/notes/note-999").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    void returnsOnlyPublishedArticlesForPublicList() throws Exception {
        mockMvc.perform(get("/api/public/articles"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].slug").exists())
                .andExpect(jsonPath("$[?(@.slug=='why-agent-first')]").doesNotExist());
    }

    @Test
    void returnsPublishedArticleDetailBySlug() throws Exception {
        mockMvc.perform(get("/api/public/articles/super-personal-workbench-reframe"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slug").value("super-personal-workbench-reframe"))
                .andExpect(jsonPath("$.markdownContent").value(org.hamcrest.Matchers.containsString("双面系统")));
    }

    @Test
    void returnsNotFoundForUnknownOrUnpublishedPublicArticle() throws Exception {
        mockMvc.perform(get("/api/public/articles/why-agent-first"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));

        mockMvc.perform(get("/api/public/articles/missing-slug"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    void createsKnowledgeAssetAndUpdatesMarkdownContent() throws Exception {
        String noteId = createNoteAndReturnId();

        mockMvc.perform(get("/api/admin/notes/" + noteId).header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Local Loop Note"))
                .andExpect(jsonPath("$.published").value(false))
                .andExpect(jsonPath("$.visibility").value("private"));

        mockMvc.perform(patch("/api/admin/notes/" + noteId)
                        .header("Cookie", OWNER_COOKIE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "New Local Loop Note",
                                  "parentId": "folder-product-reframe",
                                  "excerpt": "更新后的摘要",
                                  "markdownContent": "# New Local Loop Note\\n\\n这里是更新后的正文。"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.excerpt").value("更新后的摘要"))
                .andExpect(jsonPath("$.markdownContent").value(org.hamcrest.Matchers.containsString("更新后的正文")));
    }

    @Test
    void publishesAndUnpublishesKnowledgeAssetWithStableSlug() throws Exception {
        String noteId = createNoteAndReturnId();

        String body = mockMvc.perform(post("/api/admin/notes/" + noteId + "/publish")
                        .header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.published").value(true))
                .andExpect(jsonPath("$.visibility").value("public"))
                .andExpect(jsonPath("$.slug").value("new-local-loop-note"))
                .andReturn()
                .getResponse()
                .getContentAsString();

        JsonNode payload = objectMapper.readTree(body);
        String slug = payload.get("slug").asText();

        mockMvc.perform(get("/api/public/articles"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.slug=='" + slug + "')]").exists());

        mockMvc.perform(get("/api/public/articles/" + slug))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.slug").value(slug));

        mockMvc.perform(post("/api/admin/notes/" + noteId + "/unpublish")
                        .header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.published").value(false))
                .andExpect(jsonPath("$.visibility").value("private"))
                .andExpect(jsonPath("$.slug").value(slug));

        mockMvc.perform(get("/api/public/articles/" + slug))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    private String createNoteAndReturnId() throws Exception {
        String body = mockMvc.perform(post("/api/admin/notes")
                        .header("Cookie", OWNER_COOKIE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "New Local Loop Note",
                                  "parentId": "folder-product-reframe",
                                  "excerpt": "新建知识摘要",
                                  "markdownContent": "# New Local Loop Note\\n\\n这是第一次创建时的正文。"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isString())
                .andReturn()
                .getResponse()
                .getContentAsString();

        return objectMapper.readTree(body).get("id").asText();
    }
}
