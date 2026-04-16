package com.inkdesk.server.knowledge;

import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
@Sql(scripts = {"/testdata/cleanup.sql", "/testdata/knowledge-fixtures.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
class KnowledgeRepositoryTest {

    @Autowired
    private ContentNodeRepository contentNodeRepository;

    @Test
    void findsPublishedArticlesOnly() {
        var publishedNodes = contentNodeRepository.findPublishedNotesWithRelations();

        assertThat(publishedNodes)
                .extracting(node -> node.getPublication().getSlug())
                .containsExactlyInAnyOrder("super-personal-workbench-reframe", "public-blog-author-portal");
    }

    @Test
    void loadsAdminNoteWithDocumentTagsAndPublication() {
        var note = contentNodeRepository.findNoteByIdWithRelations("note-001");

        assertThat(note).isPresent();
        assertThat(note.get().getNoteDocument()).isNotNull();
        assertThat(note.get().getTags()).hasSize(3);
        assertThat(note.get().getPublication()).isNotNull();
    }
}
