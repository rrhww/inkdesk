package com.inkdesk.server.home;

import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.NoteDocumentEntity;
import com.inkdesk.server.knowledge.persistence.PublicationEntity;
import com.inkdesk.server.plans.PlanEntity;
import com.inkdesk.server.plans.PlanHorizon;
import com.inkdesk.server.plans.PlanPriority;
import com.inkdesk.server.plans.PlanRepository;
import com.inkdesk.server.plans.PlanStatus;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class HomeQueryServiceTest {

    @Mock
    private PlanRepository planRepository;

    @Mock
    private ContentNodeRepository contentNodeRepository;

    @InjectMocks
    private HomeQueryService homeQueryService;

    @Test
    void fallsBackToLatestPlanWhenAllPlansAreDone() {
        var olderPlan = plan("plan-done-older", PlanStatus.DONE, PlanHorizon.NEXT, PlanPriority.STEADY, Instant.parse("2026-04-12T08:00:00Z"), "旧计划");
        var latestPlan = plan("plan-done-latest", PlanStatus.DONE, PlanHorizon.TODAY, PlanPriority.CRITICAL, Instant.parse("2026-04-12T10:00:00Z"), "最新已完成计划");
        var publicNote = note("note-public", "公开知识", Instant.parse("2026-04-12T09:00:00Z"), true);

        when(planRepository.findByWorkspaceSlugWithRelatedNotes("inkdesk")).thenReturn(List.of(olderPlan, latestPlan));
        when(contentNodeRepository.findTreeByWorkspaceSlugWithRelations("inkdesk")).thenReturn(List.of(publicNote));

        var snapshot = homeQueryService.getHomeSnapshot();

        assertThat(snapshot.focusPlan()).isNotNull();
        assertThat(snapshot.focusPlan().id()).isEqualTo("plan-done-latest");
    }

    @Test
    void fallsBackToLatestKnowledgeAndBuildsEmptyPublishQueueWhenNoPrivateNotesExist() {
        var activePlan = plan("plan-001", PlanStatus.ACTIVE, PlanHorizon.TODAY, PlanPriority.CRITICAL, Instant.parse("2026-04-12T10:00:00Z"), "当前计划");
        var latestPublicNote = note("note-public-latest", "最新公开知识", Instant.parse("2026-04-12T09:30:00Z"), true);
        var olderPublicNote = note("note-public-older", "较早公开知识", Instant.parse("2026-04-12T08:30:00Z"), true);

        when(planRepository.findByWorkspaceSlugWithRelatedNotes("inkdesk")).thenReturn(List.of(activePlan));
        when(contentNodeRepository.findTreeByWorkspaceSlugWithRelations("inkdesk")).thenReturn(List.of(latestPublicNote, olderPublicNote));

        var snapshot = homeQueryService.getHomeSnapshot();

        assertThat(snapshot.focusNote()).isNotNull();
        assertThat(snapshot.focusNote().id()).isEqualTo("note-public-latest");
        assertThat(snapshot.publishQueue()).isEmpty();
        assertThat(snapshot.suggestions())
                .filteredOn(suggestion -> suggestion.id().equals("agent-003"))
                .singleElement()
                .extracting(AdminHomeSuggestionResponse::title)
                .isEqualTo("当前没有待同步到公共面的知识资产");
    }

    @Test
    void returnsEmptyKnowledgeCollectionsWithoutThrowingWhenKnowledgeIsAbsent() {
        var activePlan = plan("plan-001", PlanStatus.ACTIVE, PlanHorizon.THIS_WEEK, PlanPriority.FOCUS, Instant.parse("2026-04-12T10:00:00Z"), "当前计划");

        when(planRepository.findByWorkspaceSlugWithRelatedNotes("inkdesk")).thenReturn(List.of(activePlan));
        when(contentNodeRepository.findTreeByWorkspaceSlugWithRelations("inkdesk")).thenReturn(List.of());

        var snapshot = homeQueryService.getHomeSnapshot();

        assertThat(snapshot.focusNote()).isNull();
        assertThat(snapshot.recentKnowledge()).isEmpty();
        assertThat(snapshot.publishQueue()).isEmpty();
    }

    private PlanEntity plan(
            String id,
            PlanStatus status,
            PlanHorizon horizon,
            PlanPriority priority,
            Instant updatedAt,
            String title
    ) {
        PlanEntity plan = new PlanEntity();
        plan.setId(id);
        plan.setTitle(title);
        plan.setSummary(title + " 摘要");
        plan.setStatus(status);
        plan.setHorizon(horizon);
        plan.setPriority(priority);
        plan.setFocusLabel("焦点");
        plan.setNextStep(title + " 的下一步");
        plan.setNextActionLabel("查看计划");
        plan.setNextActionHref("/app/plans");
        plan.setSearchTerm("Agent");
        plan.setAgentPrompt(title + " 的提示");
        plan.setCreatedAt(updatedAt);
        plan.setUpdatedAt(updatedAt);
        plan.setRelatedNotes(Set.of());
        return plan;
    }

    private ContentNodeEntity note(String id, String title, Instant updatedAt, boolean published) {
        ContentNodeEntity note = new ContentNodeEntity();
        note.setId(id);
        note.setType(NodeType.NOTE);
        note.setTitle(title);
        note.setSortOrder(100);
        note.setStatus("ACTIVE");
        note.setCreatedAt(updatedAt);
        note.setUpdatedAt(updatedAt);

        ContentNodeEntity folder = new ContentNodeEntity();
        folder.setId("folder-" + id);
        folder.setType(NodeType.FOLDER);
        folder.setTitle("知识资产");
        folder.setSortOrder(1);
        folder.setStatus("ACTIVE");
        folder.setCreatedAt(updatedAt);
        folder.setUpdatedAt(updatedAt);
        note.setParent(folder);

        NoteDocumentEntity document = new NoteDocumentEntity();
        document.setId("doc-" + id);
        document.setNote(note);
        document.setMarkdownContent("# " + title);
        document.setExcerpt(title + " 摘要");
        document.setWordCount(120);
        document.setUpdatedAt(updatedAt);
        note.setNoteDocument(document);

        if (published) {
            PublicationEntity publication = new PublicationEntity();
            publication.setId("pub-" + id);
            publication.setNote(note);
            publication.setSlug(id + "-slug");
            publication.setStatus(PublicationStatus.PUBLISHED);
            publication.setPublishedAt(updatedAt);
            publication.setUpdatedAt(updatedAt);
            note.setPublication(publication);
        }

        return note;
    }
}
