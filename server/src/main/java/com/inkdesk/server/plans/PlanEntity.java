package com.inkdesk.server.plans;

import com.inkdesk.server.knowledge.persistence.ContentNodeEntity;
import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Set;

@Entity
@Table(name = "plans")
public class PlanEntity {

    @Id
    @Column(length = 64, nullable = false)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "workspace_id", nullable = false)
    private WorkspaceEntity workspace;

    @Column(nullable = false, length = 240)
    private String title;

    @Column(nullable = false)
    private String summary;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PlanStatus status;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PlanHorizon horizon;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PlanPriority priority;

    @Column(name = "focus_label", nullable = false, length = 120)
    private String focusLabel;

    @Column(name = "next_step", nullable = false)
    private String nextStep;

    @Column(name = "next_action_label", nullable = false, length = 120)
    private String nextActionLabel;

    @Column(name = "next_action_href", nullable = false, length = 240)
    private String nextActionHref;

    @Column(name = "search_term", length = 160)
    private String searchTerm;

    @Column(name = "agent_prompt", nullable = false)
    private String agentPrompt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "plan_notes",
            joinColumns = @JoinColumn(name = "plan_id"),
            inverseJoinColumns = @JoinColumn(name = "note_id")
    )
    private Set<ContentNodeEntity> relatedNotes = new LinkedHashSet<>();

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public WorkspaceEntity getWorkspace() {
        return workspace;
    }

    public void setWorkspace(WorkspaceEntity workspace) {
        this.workspace = workspace;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public PlanStatus getStatus() {
        return status;
    }

    public void setStatus(PlanStatus status) {
        this.status = status;
    }

    public PlanHorizon getHorizon() {
        return horizon;
    }

    public void setHorizon(PlanHorizon horizon) {
        this.horizon = horizon;
    }

    public PlanPriority getPriority() {
        return priority;
    }

    public void setPriority(PlanPriority priority) {
        this.priority = priority;
    }

    public String getFocusLabel() {
        return focusLabel;
    }

    public void setFocusLabel(String focusLabel) {
        this.focusLabel = focusLabel;
    }

    public String getNextStep() {
        return nextStep;
    }

    public void setNextStep(String nextStep) {
        this.nextStep = nextStep;
    }

    public String getNextActionLabel() {
        return nextActionLabel;
    }

    public void setNextActionLabel(String nextActionLabel) {
        this.nextActionLabel = nextActionLabel;
    }

    public String getNextActionHref() {
        return nextActionHref;
    }

    public void setNextActionHref(String nextActionHref) {
        this.nextActionHref = nextActionHref;
    }

    public String getSearchTerm() {
        return searchTerm;
    }

    public void setSearchTerm(String searchTerm) {
        this.searchTerm = searchTerm;
    }

    public String getAgentPrompt() {
        return agentPrompt;
    }

    public void setAgentPrompt(String agentPrompt) {
        this.agentPrompt = agentPrompt;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    public Set<ContentNodeEntity> getRelatedNotes() {
        return relatedNotes;
    }

    public void setRelatedNotes(Set<ContentNodeEntity> relatedNotes) {
        this.relatedNotes = relatedNotes;
    }
}
