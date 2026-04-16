package com.inkdesk.server.plans;

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
@Sql(
        scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql", "/testdata/plans-fixtures.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD
)
class PlanApiIntegrationTest {

    private static final String OWNER_COOKIE = "inkdesk_owner_session=owner";

    @Autowired
    private MockMvc mockMvc;

    @Test
    void requiresOwnerCookieForPlanList() throws Exception {
        mockMvc.perform(get("/api/admin/plans"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void returnsPlanListWithLinkedNoteIds() throws Exception {
        mockMvc.perform(get("/api/admin/plans").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(4))
                .andExpect(jsonPath("$[0].id").value("plan-001"))
                .andExpect(jsonPath("$[0].relatedNoteIds[0]").exists())
                .andExpect(jsonPath("$[?(@.id=='plan-004')].relatedNoteIds").isArray());
    }

    @Test
    void createsPlanWithLinkedKnowledge() throws Exception {
        mockMvc.perform(post("/api/admin/plans")
                        .header("Cookie", OWNER_COOKIE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "把计划写接口接到真实数据",
                                  "summary": "先补齐计划创建与更新接口。",
                                  "status": "active",
                                  "horizon": "today",
                                  "priority": "focus",
                                  "focusLabel": "计划闭环",
                                  "nextStep": "把计划写模型和前端动作统一起来。",
                                  "nextActionLabel": "打开计划控制台",
                                  "nextActionHref": "/app/plans",
                                  "searchTerm": "计划",
                                  "agentPrompt": "围绕计划闭环补齐写模型与前端动作。",
                                  "relatedNoteIds": ["note-001"]
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("把计划写接口接到真实数据"))
                .andExpect(jsonPath("$.status").value("active"))
                .andExpect(jsonPath("$.statusLabel").value("进行中"))
                .andExpect(jsonPath("$.relatedNoteIds[0]").value("note-001"));

        mockMvc.perform(get("/api/admin/plans").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.title=='把计划写接口接到真实数据')]").exists());
    }

    @Test
    void updatesPlanStatusAndRelatedNotes() throws Exception {
        mockMvc.perform(patch("/api/admin/plans/plan-001")
                        .header("Cookie", OWNER_COOKIE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "重构公共面与主系统的双面入口",
                                  "summary": "更新后的计划摘要",
                                  "status": "done",
                                  "horizon": "this-week",
                                  "priority": "steady",
                                  "focusLabel": "双面入口",
                                  "nextStep": "收口验证清单。",
                                  "nextActionLabel": "回到计划控制台",
                                  "nextActionHref": "/app/plans",
                                  "searchTerm": "公开面",
                                  "agentPrompt": "验证这条计划已经收口。",
                                  "relatedNoteIds": ["note-002"]
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value("plan-001"))
                .andExpect(jsonPath("$.status").value("done"))
                .andExpect(jsonPath("$.statusLabel").value("已完成"))
                .andExpect(jsonPath("$.relatedNoteIds[0]").value("note-002"));

        mockMvc.perform(get("/api/admin/plans").header("Cookie", OWNER_COOKIE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.id=='plan-001')].status").value("done"));
    }

    @Test
    void returnsControlledErrorWhenRelatedKnowledgeIsMissing() throws Exception {
        mockMvc.perform(post("/api/admin/plans")
                        .header("Cookie", OWNER_COOKIE)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "title": "关联缺失知识",
                                  "summary": "应该返回受控错误。",
                                  "status": "queued",
                                  "horizon": "next",
                                  "priority": "steady",
                                  "focusLabel": "错误处理",
                                  "nextStep": "验证缺失关联知识时不抛 500。",
                                  "nextActionLabel": "查看计划",
                                  "nextActionHref": "/app/plans",
                                  "searchTerm": "错误处理",
                                  "agentPrompt": "确认缺失关联知识时返回受控错误。",
                                  "relatedNoteIds": ["note-missing"]
                                }
                                """))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }
}
