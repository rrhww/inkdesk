package com.inkdesk.server.plans;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

@Service
public class PlanCommandService {

    private static final String DEFAULT_WORKSPACE_SLUG = "inkdesk";

    private final PlanRepository planRepository;
    private final WorkspaceRepository workspaceRepository;
    private final ContentNodeRepository contentNodeRepository;

    public PlanCommandService(
            PlanRepository planRepository,
            WorkspaceRepository workspaceRepository,
            ContentNodeRepository contentNodeRepository
    ) {
        this.planRepository = planRepository;
        this.workspaceRepository = workspaceRepository;
        this.contentNodeRepository = contentNodeRepository;
    }

    @Transactional
    public PlanListItemResponse createPlan(PlanUpsertRequest request) {
        WorkspaceEntity workspace = workspaceRepository.findBySlug(DEFAULT_WORKSPACE_SLUG)
                .orElseThrow(() -> new ResourceNotFoundException("Workspace not found: " + DEFAULT_WORKSPACE_SLUG));
        Instant now = Instant.now();

        PlanEntity plan = new PlanEntity();
        plan.setId("plan-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12));
        plan.setWorkspace(workspace);
        apply(plan, request, now);

        return toResponse(planRepository.save(plan));
    }

    @Transactional
    public PlanListItemResponse updatePlan(String planId, PlanUpsertRequest request) {
        PlanEntity plan = planRepository.findById(planId)
                .orElseThrow(() -> new ResourceNotFoundException("Plan not found: " + planId));

        apply(plan, request, Instant.now());

        return toResponse(planRepository.save(plan));
    }

    private void apply(PlanEntity plan, PlanUpsertRequest request, Instant updatedAt) {
        plan.setTitle(request.title());
        plan.setSummary(request.summary());
        plan.setStatus(parseStatus(request.status()));
        plan.setHorizon(parseHorizon(request.horizon()));
        plan.setPriority(parsePriority(request.priority()));
        plan.setFocusLabel(request.focusLabel());
        plan.setNextStep(request.nextStep());
        plan.setNextActionLabel(request.nextActionLabel());
        plan.setNextActionHref(request.nextActionHref());
        plan.setSearchTerm(request.searchTerm());
        plan.setAgentPrompt(request.agentPrompt());
        if (plan.getCreatedAt() == null) {
            plan.setCreatedAt(updatedAt);
        }
        plan.setUpdatedAt(updatedAt);
        plan.setRelatedNotes(resolveRelatedNotes(request.relatedNoteIds()));
    }

    private Set<ContentNodeEntity> resolveRelatedNotes(List<String> relatedNoteIds) {
        if (relatedNoteIds == null || relatedNoteIds.isEmpty()) {
            return new LinkedHashSet<>();
        }

        List<ContentNodeEntity> notes = contentNodeRepository.findAllById(relatedNoteIds).stream()
                .filter(node -> node.getType() == NodeType.NOTE)
                .toList();

        if (notes.size() != relatedNoteIds.size()) {
            throw new ResourceNotFoundException("One or more related knowledge assets were not found.");
        }

        return new LinkedHashSet<>(notes);
    }

    private PlanStatus parseStatus(String value) {
        return switch (value) {
            case "active" -> PlanStatus.ACTIVE;
            case "queued" -> PlanStatus.QUEUED;
            case "done" -> PlanStatus.DONE;
            default -> throw new IllegalArgumentException("Unsupported plan status: " + value);
        };
    }

    private PlanHorizon parseHorizon(String value) {
        return switch (value) {
            case "today" -> PlanHorizon.TODAY;
            case "this-week" -> PlanHorizon.THIS_WEEK;
            case "next" -> PlanHorizon.NEXT;
            default -> throw new IllegalArgumentException("Unsupported plan horizon: " + value);
        };
    }

    private PlanPriority parsePriority(String value) {
        return switch (value) {
            case "critical" -> PlanPriority.CRITICAL;
            case "focus" -> PlanPriority.FOCUS;
            case "steady" -> PlanPriority.STEADY;
            default -> throw new IllegalArgumentException("Unsupported plan priority: " + value);
        };
    }

    private PlanListItemResponse toResponse(PlanEntity plan) {
        return new PlanListItemResponse(
                plan.getId(),
                plan.getTitle(),
                plan.getSummary(),
                plan.getStatus().name().toLowerCase(),
                statusLabel(plan.getStatus()),
                horizonValue(plan.getHorizon()),
                horizonLabel(plan.getHorizon()),
                plan.getPriority().name().toLowerCase(),
                priorityLabel(plan.getPriority()),
                plan.getFocusLabel(),
                plan.getNextStep(),
                plan.getNextActionLabel(),
                plan.getNextActionHref(),
                plan.getSearchTerm(),
                plan.getAgentPrompt(),
                plan.getUpdatedAt(),
                plan.getRelatedNotes().stream().map(ContentNodeEntity::getId).sorted().toList()
        );
    }

    private String statusLabel(PlanStatus status) {
        return switch (status) {
            case ACTIVE -> "进行中";
            case QUEUED -> "待推进";
            case DONE -> "已完成";
        };
    }

    private String horizonValue(PlanHorizon horizon) {
        return switch (horizon) {
            case TODAY -> "today";
            case THIS_WEEK -> "this-week";
            case NEXT -> "next";
        };
    }

    private String horizonLabel(PlanHorizon horizon) {
        return switch (horizon) {
            case TODAY -> "今天";
            case THIS_WEEK -> "本周";
            case NEXT -> "下一步";
        };
    }

    private String priorityLabel(PlanPriority priority) {
        return switch (priority) {
            case CRITICAL -> "最高优先级";
            case FOCUS -> "当前主线";
            case STEADY -> "下一轮整理";
        };
    }
}
