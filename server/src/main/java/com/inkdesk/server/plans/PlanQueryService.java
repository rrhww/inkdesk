package com.inkdesk.server.plans;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Comparator;
import java.util.List;

@Service
public class PlanQueryService {

    private static final String DEFAULT_WORKSPACE_SLUG = "inkdesk";

    private final PlanRepository planRepository;

    public PlanQueryService(PlanRepository planRepository) {
        this.planRepository = planRepository;
    }

    @Transactional(readOnly = true)
    public List<PlanListItemResponse> getPlans() {
        return planRepository.findByWorkspaceSlugWithRelatedNotes(DEFAULT_WORKSPACE_SLUG).stream()
                .sorted(Comparator.comparing(PlanEntity::getUpdatedAt).reversed())
                .map(this::toResponse)
                .toList();
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
                plan.getRelatedNotes().stream()
                        .map(note -> note.getId())
                        .sorted()
                        .toList()
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
