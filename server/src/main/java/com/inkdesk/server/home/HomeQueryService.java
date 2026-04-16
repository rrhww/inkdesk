package com.inkdesk.server.home;

import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.plans.PlanEntity;
import com.inkdesk.server.plans.PlanHorizon;
import com.inkdesk.server.plans.PlanPriority;
import com.inkdesk.server.plans.PlanRepository;
import com.inkdesk.server.plans.PlanStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

@Service
public class HomeQueryService {

    private static final String DEFAULT_WORKSPACE_SLUG = "inkdesk";

    private final PlanRepository planRepository;
    private final ContentNodeRepository contentNodeRepository;

    public HomeQueryService(PlanRepository planRepository, ContentNodeRepository contentNodeRepository) {
        this.planRepository = planRepository;
        this.contentNodeRepository = contentNodeRepository;
    }

    @Transactional(readOnly = true)
    public AdminHomeResponse getHomeSnapshot() {
        List<PlanEntity> plans = planRepository.findByWorkspaceSlugWithRelatedNotes(DEFAULT_WORKSPACE_SLUG);
        List<ContentNodeEntity> notes = contentNodeRepository.findTreeByWorkspaceSlugWithRelations(DEFAULT_WORKSPACE_SLUG).stream()
                .filter(node -> node.getType() == NodeType.NOTE)
                .toList();

        List<ContentNodeEntity> sortedNotes = notes.stream()
                .sorted(Comparator.comparing(this::noteUpdatedAt).reversed())
                .toList();

        AdminHomePlanResponse focusPlan = selectFocusPlan(plans).map(this::toFocusPlan).orElse(null);
        AdminHomeNoteResponse focusNote = selectFocusNote(sortedNotes).map(this::toHomeNote).orElse(null);
        List<AdminHomeNoteResponse> recentKnowledge = sortedNotes.stream()
                .limit(3)
                .map(this::toHomeNote)
                .toList();
        List<AdminHomePublishQueueItemResponse> publishQueue = sortedNotes.stream()
                .filter(note -> !isPublished(note))
                .map(this::toPublishQueueItem)
                .toList();

        return new AdminHomeResponse(
                new AdminHomeSummaryResponse(
                        (int) plans.stream().filter(plan -> plan.getStatus() == PlanStatus.ACTIVE).count(),
                        (int) sortedNotes.stream().filter(note -> !isPublished(note)).count(),
                        (int) sortedNotes.stream().filter(this::isPublished).count(),
                        plans.stream()
                                .flatMap(plan -> plan.getRelatedNotes().stream())
                                .map(ContentNodeEntity::getId)
                                .distinct()
                                .toList()
                                .size()
                ),
                focusPlan,
                focusNote,
                buildSuggestions(focusPlan, focusNote, publishQueue),
                buildQuickActions(focusPlan),
                recentKnowledge,
                publishQueue
        );
    }

    private Optional<PlanEntity> selectFocusPlan(List<PlanEntity> plans) {
        List<PlanEntity> nonDonePlans = plans.stream()
                .filter(plan -> plan.getStatus() != PlanStatus.DONE)
                .toList();

        if (!nonDonePlans.isEmpty()) {
            return nonDonePlans.stream()
                    .min(Comparator
                            .comparingInt((PlanEntity plan) -> horizonRank(plan.getHorizon()))
                            .thenComparingInt(plan -> priorityRank(plan.getPriority()))
                            .thenComparing(PlanEntity::getUpdatedAt, Comparator.reverseOrder()));
        }

        return plans.stream().max(Comparator.comparing(PlanEntity::getUpdatedAt));
    }

    private Optional<ContentNodeEntity> selectFocusNote(List<ContentNodeEntity> sortedNotes) {
        return sortedNotes.stream()
                .filter(note -> !isPublished(note))
                .findFirst()
                .or(() -> sortedNotes.stream().findFirst());
    }

    private AdminHomePlanResponse toFocusPlan(PlanEntity plan) {
        return new AdminHomePlanResponse(
                plan.getId(),
                plan.getTitle(),
                statusLabel(plan.getStatus()),
                horizonLabel(plan.getHorizon()),
                priorityLabel(plan.getPriority()),
                plan.getNextStep(),
                plan.getNextActionLabel(),
                plan.getNextActionHref(),
                blankToNull(plan.getSearchTerm())
        );
    }

    private AdminHomeNoteResponse toHomeNote(ContentNodeEntity note) {
        String visibility = isPublished(note) ? "public" : "private";

        return new AdminHomeNoteResponse(
                note.getId(),
                note.getTitle(),
                note.getNoteDocument() != null && note.getNoteDocument().getExcerpt() != null ? note.getNoteDocument().getExcerpt() : "",
                note.getParent() != null ? note.getParent().getTitle() : "知识资产",
                noteUpdatedAt(note),
                isPublished(note),
                visibility,
                visibility.equals("public") ? "公共面 + 主系统" : "仅主系统"
        );
    }

    private AdminHomePublishQueueItemResponse toPublishQueueItem(ContentNodeEntity note) {
        return new AdminHomePublishQueueItemResponse(
                note.getId(),
                note.getTitle(),
                note.getNoteDocument() != null && note.getNoteDocument().getExcerpt() != null ? note.getNoteDocument().getExcerpt() : "",
                noteUpdatedAt(note),
                "draft",
                "继续整理后同步"
        );
    }

    private List<AdminHomeSuggestionResponse> buildSuggestions(
            AdminHomePlanResponse focusPlan,
            AdminHomeNoteResponse focusNote,
            List<AdminHomePublishQueueItemResponse> publishQueue
    ) {
        AdminHomeSuggestionResponse planSuggestion = focusPlan != null
                ? new AdminHomeSuggestionResponse(
                        "agent-001",
                        "今日建议",
                        "围绕「" + focusPlan.title() + "」推进下一步",
                        focusPlan.nextStep(),
                        focusPlan.nextActionLabel(),
                        focusPlan.nextActionHref()
                )
                : new AdminHomeSuggestionResponse(
                        "agent-001",
                        "今日建议",
                        "先建立今天最重要的一条计划",
                        "当前还没有可推进的计划，先回到计划模块固定下一步动作。",
                        "查看任务与计划",
                        "/app/plans"
                );

        AdminHomeSuggestionResponse knowledgeSuggestion = focusNote != null
                ? new AdminHomeSuggestionResponse(
                        "agent-002",
                        "知识建议",
                        "回到「" + focusNote.title() + "」补齐当前判断",
                        focusNote.excerpt(),
                        "查看知识资产",
                        noteHref(focusNote)
                )
                : new AdminHomeSuggestionResponse(
                        "agent-002",
                        "知识建议",
                        "补一条新的知识资产",
                        "当前还没有可回看的知识资产，先记录下一条判断。",
                        "新建知识资产",
                        "/app/notes/new-note?state=blank"
                );

        AdminHomeSuggestionResponse publishSuggestion = publishQueue.isEmpty()
                ? new AdminHomeSuggestionResponse(
                        "agent-003",
                        "发布建议",
                        "当前没有待同步到公共面的知识资产",
                        "发布队列目前为空，可以继续打磨新的内部知识。",
                        "打开发布模块",
                        "/app/publish"
                )
                : new AdminHomeSuggestionResponse(
                        "agent-003",
                        "发布建议",
                        "当前有 " + publishQueue.size() + " 篇知识资产待同步到公共面",
                        "优先检查哪些知识已经成熟到可以整理后发布。",
                        "打开发布模块",
                        "/app/publish"
                );

        return List.of(planSuggestion, knowledgeSuggestion, publishSuggestion);
    }

    private List<AdminHomeQuickActionResponse> buildQuickActions(AdminHomePlanResponse focusPlan) {
        String searchTerm = focusPlan != null && focusPlan.searchTerm() != null && !focusPlan.searchTerm().isBlank()
                ? focusPlan.searchTerm()
                : "Agent";

        return List.of(
                new AdminHomeQuickActionResponse(
                        "quick-001",
                        "新建知识资产",
                        "直接进入知识资产工作台，开始记录新的判断。",
                        "/app/notes/new-note?state=blank",
                        "edit_note"
                ),
                new AdminHomeQuickActionResponse(
                        "quick-002",
                        "创建计划",
                        "回到计划控制台，把下一步动作固定下来。",
                        "/app/plans",
                        "playlist_add_check_circle"
                ),
                new AdminHomeQuickActionResponse(
                        "quick-003",
                        "继续检索",
                        "把相关上下文重新带回当前工作流。",
                        "/app/search?q=" + URLEncoder.encode(searchTerm, StandardCharsets.UTF_8),
                        "travel_explore"
                ),
                new AdminHomeQuickActionResponse(
                        "quick-004",
                        "进入发布",
                        "检查哪些知识资产已经成熟到可以同步到公共面。",
                        "/app/publish",
                        "ios_share"
                )
        );
    }

    private String noteHref(AdminHomeNoteResponse note) {
        return note.published()
                ? "/app/notes/" + note.id() + "?state=published"
                : "/app/notes/" + note.id();
    }

    private Instant noteUpdatedAt(ContentNodeEntity note) {
        if (note.getNoteDocument() != null && note.getNoteDocument().getUpdatedAt() != null) {
            return note.getNoteDocument().getUpdatedAt();
        }

        return note.getUpdatedAt();
    }

    private boolean isPublished(ContentNodeEntity note) {
        return note.getPublication() != null && note.getPublication().getStatus() == PublicationStatus.PUBLISHED;
    }

    private int horizonRank(PlanHorizon horizon) {
        if (horizon == null) {
            return Integer.MAX_VALUE;
        }

        return switch (horizon) {
            case TODAY -> 0;
            case THIS_WEEK -> 1;
            case NEXT -> 2;
        };
    }

    private int priorityRank(PlanPriority priority) {
        if (priority == null) {
            return Integer.MAX_VALUE;
        }

        return switch (priority) {
            case CRITICAL -> 0;
            case FOCUS -> 1;
            case STEADY -> 2;
        };
    }

    private String statusLabel(PlanStatus status) {
        return switch (Objects.requireNonNull(status)) {
            case ACTIVE -> "进行中";
            case QUEUED -> "待推进";
            case DONE -> "已完成";
        };
    }

    private String horizonLabel(PlanHorizon horizon) {
        return switch (Objects.requireNonNull(horizon)) {
            case TODAY -> "今天";
            case THIS_WEEK -> "本周";
            case NEXT -> "下一步";
        };
    }

    private String priorityLabel(PlanPriority priority) {
        return switch (Objects.requireNonNull(priority)) {
            case CRITICAL -> "最高优先级";
            case FOCUS -> "当前主线";
            case STEADY -> "下一轮整理";
        };
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }
}
