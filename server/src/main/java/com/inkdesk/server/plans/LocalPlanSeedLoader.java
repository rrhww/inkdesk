package com.inkdesk.server.plans;

import com.inkdesk.server.knowledge.persistence.ContentNodeRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Set;

@Component
@Profile("local")
@Order(20)
public class LocalPlanSeedLoader implements ApplicationRunner {

    private final PlanRepository planRepository;
    private final WorkspaceRepository workspaceRepository;
    private final ContentNodeRepository contentNodeRepository;

    public LocalPlanSeedLoader(
            PlanRepository planRepository,
            WorkspaceRepository workspaceRepository,
            ContentNodeRepository contentNodeRepository
    ) {
        this.planRepository = planRepository;
        this.workspaceRepository = workspaceRepository;
        this.contentNodeRepository = contentNodeRepository;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        var workspace = workspaceRepository.findBySlug("inkdesk").orElse(null);
        if (workspace == null) {
            return;
        }

        ensurePlan(buildPlan(
                workspace,
                "plan-001",
                "重构公共面与主系统的双面入口",
                "先把公开博客入口、隐藏登录入口和主系统骨架彻底分开。",
                PlanStatus.ACTIVE,
                PlanHorizon.TODAY,
                PlanPriority.CRITICAL,
                "系统入口",
                "把访客入口、隐藏登录和主系统跳转链路再检查一轮。",
                "检查入口链路",
                "/app/search?q=%E5%85%AC%E5%85%B1%E9%9D%A2",
                "公共面",
                "把双面系统的入口规则压缩成一份可执行检查清单。",
                Instant.parse("2026-04-12T10:30:00Z"),
                Set.of("note-003", "note-001")
        ));

        ensurePlan(buildPlan(
                workspace,
                "plan-002",
                "补齐 Agent 控制台的核心模块",
                "让首页真正具备上下文汇总、任务推进和知识召回三个功能面。",
                PlanStatus.ACTIVE,
                PlanHorizon.THIS_WEEK,
                PlanPriority.FOCUS,
                "Agent 首页",
                "把 Agent 首页与任务、知识中枢之间的跳转再压缩成更短的行动路径。",
                "打开 Agent 控制台",
                "/app",
                "Agent",
                "从当前笔记和计划里提炼今天最值得推进的一件事。",
                Instant.parse("2026-04-12T09:56:00Z"),
                Set.of("note-001", "note-002")
        ));

        ensurePlan(buildPlan(
                workspace,
                "plan-003",
                "让发布模块退到次级位置",
                "保留公开输出能力，但不再让它主导整个平台的叙事与导航。",
                PlanStatus.QUEUED,
                PlanHorizon.NEXT,
                PlanPriority.STEADY,
                "公共输出",
                "只保留稳定的知识输出路径，把公开文章继续留在次级模块里。",
                "查看发布模块",
                "/app/publish",
                "公开文章",
                "判断哪些知识资产已经成熟到可以同步到公共面。",
                Instant.parse("2026-04-12T09:10:00Z"),
                Set.of("note-003")
        ));
    }

    private void ensurePlan(PlanEntity plan) {
        if (planRepository.existsById(plan.getId())) {
            return;
        }

        planRepository.save(plan);
    }

    private PlanEntity buildPlan(
            WorkspaceEntity workspace,
            String id,
            String title,
            String summary,
            PlanStatus status,
            PlanHorizon horizon,
            PlanPriority priority,
            String focusLabel,
            String nextStep,
            String nextActionLabel,
            String nextActionHref,
            String searchTerm,
            String agentPrompt,
            Instant updatedAt,
            Set<String> relatedNoteIds
    ) {
        PlanEntity plan = new PlanEntity();
        plan.setId(id);
        plan.setWorkspace(workspace);
        plan.setTitle(title);
        plan.setSummary(summary);
        plan.setStatus(status);
        plan.setHorizon(horizon);
        plan.setPriority(priority);
        plan.setFocusLabel(focusLabel);
        plan.setNextStep(nextStep);
        plan.setNextActionLabel(nextActionLabel);
        plan.setNextActionHref(nextActionHref);
        plan.setSearchTerm(searchTerm);
        plan.setAgentPrompt(agentPrompt);
        plan.setCreatedAt(updatedAt);
        plan.setUpdatedAt(updatedAt);
        plan.setRelatedNotes(new LinkedHashSet<>(relatedNoteIds.stream()
                .map(contentNodeRepository::findNoteByIdWithRelations)
                .flatMap(Optional -> Optional.stream())
                .toList()));
        return plan;
    }
}
