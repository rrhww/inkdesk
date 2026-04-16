package com.inkdesk.server.settings;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.MapsId;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;

import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;

import java.time.Instant;

@Entity
@Table(name = "workspace_settings")
public class WorkspaceSettingsEntity {

    @Id
    @Column(name = "workspace_id", length = 64, nullable = false)
    private String workspaceId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "workspace_id", nullable = false)
    private WorkspaceEntity workspace;

    @Column(name = "display_name", length = 120, nullable = false)
    private String displayName;

    @Column(name = "public_title", length = 240, nullable = false)
    private String publicTitle;

    @Column(nullable = false)
    private String summary;

    @Column(name = "public_location", length = 120, nullable = false)
    private String publicLocation;

    @Column(name = "default_page", length = 120, nullable = false)
    private String defaultPage;

    @Column(name = "compact_mode", nullable = false)
    private boolean compactMode;

    @Column(name = "show_context_ribbon", nullable = false)
    private boolean showContextRibbon;

    @Column(name = "editor_default_view", length = 20, nullable = false)
    private String editorDefaultView;

    @Column(name = "editor_auto_save", nullable = false)
    private boolean editorAutoSave;

    @Column(name = "editor_publish_reminder", nullable = false)
    private boolean editorPublishReminder;

    @Column(name = "publish_default_audience", length = 20, nullable = false)
    private String publishDefaultAudience;

    @Column(name = "publish_show_provenance", nullable = false)
    private boolean publishShowProvenance;

    @Column(name = "publish_highlight_recent_updates", nullable = false)
    private boolean publishHighlightRecentUpdates;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public void setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
    }

    public WorkspaceEntity getWorkspace() {
        return workspace;
    }

    public void setWorkspace(WorkspaceEntity workspace) {
        this.workspace = workspace;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public String getPublicTitle() {
        return publicTitle;
    }

    public void setPublicTitle(String publicTitle) {
        this.publicTitle = publicTitle;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getPublicLocation() {
        return publicLocation;
    }

    public void setPublicLocation(String publicLocation) {
        this.publicLocation = publicLocation;
    }

    public String getDefaultPage() {
        return defaultPage;
    }

    public void setDefaultPage(String defaultPage) {
        this.defaultPage = defaultPage;
    }

    public boolean isCompactMode() {
        return compactMode;
    }

    public void setCompactMode(boolean compactMode) {
        this.compactMode = compactMode;
    }

    public boolean isShowContextRibbon() {
        return showContextRibbon;
    }

    public void setShowContextRibbon(boolean showContextRibbon) {
        this.showContextRibbon = showContextRibbon;
    }

    public String getEditorDefaultView() {
        return editorDefaultView;
    }

    public void setEditorDefaultView(String editorDefaultView) {
        this.editorDefaultView = editorDefaultView;
    }

    public boolean isEditorAutoSave() {
        return editorAutoSave;
    }

    public void setEditorAutoSave(boolean editorAutoSave) {
        this.editorAutoSave = editorAutoSave;
    }

    public boolean isEditorPublishReminder() {
        return editorPublishReminder;
    }

    public void setEditorPublishReminder(boolean editorPublishReminder) {
        this.editorPublishReminder = editorPublishReminder;
    }

    public String getPublishDefaultAudience() {
        return publishDefaultAudience;
    }

    public void setPublishDefaultAudience(String publishDefaultAudience) {
        this.publishDefaultAudience = publishDefaultAudience;
    }

    public boolean isPublishShowProvenance() {
        return publishShowProvenance;
    }

    public void setPublishShowProvenance(boolean publishShowProvenance) {
        this.publishShowProvenance = publishShowProvenance;
    }

    public boolean isPublishHighlightRecentUpdates() {
        return publishHighlightRecentUpdates;
    }

    public void setPublishHighlightRecentUpdates(boolean publishHighlightRecentUpdates) {
        this.publishHighlightRecentUpdates = publishHighlightRecentUpdates;
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
}
