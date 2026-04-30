package com.inkdesk.server.plans;

import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.DefaultApplicationArguments;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Sql(
        scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql", "/testdata/partial-plans.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD
)
class LocalPlanSeedLoaderIntegrationTest {

    @Autowired
    private LocalPlanSeedLoader localPlanSeedLoader;

    @Autowired
    private PlanRepository planRepository;

    @Autowired
    private WorkspaceRepository workspaceRepository;

    @Autowired
    private ContentNodeRepository contentNodeRepository;

    @Test
    void backfillsMissingDefaultPlansWhenDatabaseAlreadyContainsOnePlan() throws Exception {
        localPlanSeedLoader.run(new DefaultApplicationArguments(new String[0]));

        assertThat(planRepository.findById("plan-001")).isPresent();
        assertThat(planRepository.findById("plan-002")).isPresent();
        assertThat(planRepository.findById("plan-003")).isPresent();
        assertThat(planRepository.count()).isEqualTo(3);
    }

    @TestConfiguration
    static class LoaderConfig {

        @Bean
        LocalPlanSeedLoader localPlanSeedLoader(
                PlanRepository planRepository,
                WorkspaceRepository workspaceRepository,
                ContentNodeRepository contentNodeRepository
        ) {
            return new LocalPlanSeedLoader(planRepository, workspaceRepository, contentNodeRepository);
        }
    }
}
