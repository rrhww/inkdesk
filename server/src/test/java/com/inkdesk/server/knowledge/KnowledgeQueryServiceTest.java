package com.inkdesk.server.knowledge;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import com.inkdesk.server.knowledge.service.KnowledgeQueryService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class KnowledgeQueryServiceTest {

    @Autowired
    private KnowledgeQueryService knowledgeQueryService;

    @Test
    void aggregatesAdminNoteDetail() {
        var detail = knowledgeQueryService.getAdminNoteDetail("note-001");

        assertThat(detail.id()).isEqualTo("note-001");
        assertThat(detail.tags()).contains("定位", "超级个人工作台", "Agent");
        assertThat(detail.published()).isTrue();
    }

    @Test
    void raisesNotFoundWhenAdminNoteDoesNotExist() {
        assertThatThrownBy(() -> knowledgeQueryService.getAdminNoteDetail("note-missing"))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("note-missing");
    }
}
