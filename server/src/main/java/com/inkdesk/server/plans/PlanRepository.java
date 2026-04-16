package com.inkdesk.server.plans;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface PlanRepository extends JpaRepository<PlanEntity, String> {

    @EntityGraph(attributePaths = {"relatedNotes"})
    @Query("select distinct plan from PlanEntity plan where plan.workspace.slug = :workspaceSlug order by plan.updatedAt desc")
    List<PlanEntity> findByWorkspaceSlugWithRelatedNotes(String workspaceSlug);
}
