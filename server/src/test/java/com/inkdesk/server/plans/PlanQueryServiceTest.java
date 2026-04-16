package com.inkdesk.server.plans;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Sql(
        scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql", "/testdata/plans-fixtures.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD
)
class PlanQueryServiceTest {

    @Autowired(required = false)
    private PlanQueryService planQueryService;

    @Test
    void returnsPlansOrderedByUpdatedAtDescending() {
        assertThat(planQueryService).isNotNull();

        var plans = planQueryService.getPlans();

        assertThat(plans).hasSize(4);
        assertThat(plans.get(0).id()).isEqualTo("plan-001");
        assertThat(plans.get(1).id()).isEqualTo("plan-002");
    }

    @Test
    void returnsEmptyRelatedNoteIdsWhenPlanHasNoLinks() {
        assertThat(planQueryService).isNotNull();

        var plans = planQueryService.getPlans();

        assertThat(plans)
                .filteredOn(plan -> plan.id().equals("plan-004"))
                .singleElement()
                .extracting(PlanListItemResponse::relatedNoteIds)
                .isEqualTo(java.util.List.of());
    }
}
