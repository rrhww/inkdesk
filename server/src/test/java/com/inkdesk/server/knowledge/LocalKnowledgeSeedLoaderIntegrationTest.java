package com.inkdesk.server.knowledge;

import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.TagRepository;
import com.inkdesk.server.knowledge.persistence.UserRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import com.inkdesk.server.knowledge.service.LocalKnowledgeSeedLoader;
import com.inkdesk.server.settings.WorkspaceSettingsRepository;
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
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/owner-without-settings.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class LocalKnowledgeSeedLoaderIntegrationTest {

    @Autowired
    private LocalKnowledgeSeedLoader localKnowledgeSeedLoader;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private WorkspaceRepository workspaceRepository;

    @Autowired
    private WorkspaceSettingsRepository workspaceSettingsRepository;

    @Autowired
    private TagRepository tagRepository;

    @Autowired
    private ContentNodeRepository contentNodeRepository;

    @Test
    void backfillsSettingsFoldersTagsAndNotesWhenOwnerAlreadyExists() throws Exception {
        localKnowledgeSeedLoader.run(new DefaultApplicationArguments(new String[0]));

        assertThat(userRepository.findByUsername("owner")).isPresent();
        assertThat(workspaceRepository.findBySlug("inkdesk")).isPresent();
        assertThat(workspaceSettingsRepository.findById("workspace-inkdesk")).isPresent();
        assertThat(tagRepository.findById("tag-agent")).isPresent();
        assertThat(contentNodeRepository.findById("folder-system-structure")).isPresent();
        assertThat(contentNodeRepository.findNoteByIdWithRelations("note-001")).isPresent();
        assertThat(contentNodeRepository.findNoteByIdWithRelations("note-002")).isPresent();
        assertThat(contentNodeRepository.findNoteByIdWithRelations("note-003")).isPresent();
    }

    @TestConfiguration
    static class LoaderConfig {

        @Bean
        LocalKnowledgeSeedLoader localKnowledgeSeedLoader(
                UserRepository userRepository,
                WorkspaceRepository workspaceRepository,
                WorkspaceSettingsRepository workspaceSettingsRepository,
                TagRepository tagRepository,
                ContentNodeRepository contentNodeRepository
        ) {
            return new LocalKnowledgeSeedLoader(
                    userRepository,
                    workspaceRepository,
                    workspaceSettingsRepository,
                    tagRepository,
                    contentNodeRepository
            );
        }
    }
}
