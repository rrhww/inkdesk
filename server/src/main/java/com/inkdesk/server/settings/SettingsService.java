package com.inkdesk.server.settings;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import com.inkdesk.server.knowledge.persistence.UserEntity;
import com.inkdesk.server.knowledge.persistence.UserRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceEntity;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;

@Service
public class SettingsService {

    private final UserRepository userRepository;
    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceSettingsRepository workspaceSettingsRepository;
    private final Duration sessionDuration;

    public SettingsService(
            UserRepository userRepository,
            WorkspaceRepository workspaceRepository,
            WorkspaceSettingsRepository workspaceSettingsRepository,
            @Value("${inkdesk.auth.session-duration:PT8H}") Duration sessionDuration
    ) {
        this.userRepository = userRepository;
        this.workspaceRepository = workspaceRepository;
        this.workspaceSettingsRepository = workspaceSettingsRepository;
        this.sessionDuration = sessionDuration;
    }

    @Transactional(readOnly = true)
    public SettingsResponse getSettings(String username) {
        UserEntity user = requireUser(username);
        WorkspaceEntity workspace = requireWorkspace(user);
        WorkspaceSettingsEntity settings = getOrCreateSettings(workspace);
        return toResponse(user, settings);
    }

    @Transactional
    public SettingsResponse updateSettings(String username, UpdateSettingsRequest request) {
        UserEntity user = requireUser(username);
        WorkspaceEntity workspace = requireWorkspace(user);
        WorkspaceSettingsEntity settings = getOrCreateSettings(workspace);

        settings.setDisplayName(request.profile().displayName());
        settings.setPublicTitle(request.profile().publicTitle());
        settings.setSummary(request.profile().summary());
        settings.setPublicLocation(request.profile().publicLocation());
        settings.setDefaultPage(request.workbench().defaultPage());
        settings.setCompactMode(request.workbench().compactMode());
        settings.setShowContextRibbon(request.workbench().showContextRibbon());
        settings.setEditorDefaultView(request.editor().defaultView());
        settings.setEditorAutoSave(request.editor().autoSave());
        settings.setEditorPublishReminder(request.editor().publishReminder());
        settings.setPublishDefaultAudience(request.publish().defaultAudience());
        settings.setPublishShowProvenance(request.publish().showProvenance());
        settings.setPublishHighlightRecentUpdates(request.publish().highlightRecentUpdates());
        settings.setUpdatedAt(Instant.now());

        workspaceSettingsRepository.save(settings);

        return toResponse(user, settings);
    }

    private UserEntity requireUser(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new ResourceNotFoundException("Owner profile not found for username: " + username));
    }

    private WorkspaceEntity requireWorkspace(UserEntity user) {
        return workspaceRepository.findByOwnerUserId(user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Workspace not found for owner: " + user.getId()));
    }

    private WorkspaceSettingsEntity getOrCreateSettings(WorkspaceEntity workspace) {
        return workspaceSettingsRepository.findById(workspace.getId())
                .orElseGet(() -> createDefaultSettings(workspace));
    }

    private WorkspaceSettingsEntity createDefaultSettings(WorkspaceEntity workspace) {
        Instant now = Instant.now();
        WorkspaceSettingsEntity settings = new WorkspaceSettingsEntity();
        settings.setWorkspace(workspace);
        settings.setDisplayName("R");
        settings.setPublicTitle("构建超级个人工作台的人");
        settings.setSummary("我把 Inkdesk 当成自己的长期知识与执行系统，并持续向公共面输出成熟内容。");
        settings.setPublicLocation("Shanghai");
        settings.setDefaultPage("/app");
        settings.setCompactMode(false);
        settings.setShowContextRibbon(true);
        settings.setEditorDefaultView("edit");
        settings.setEditorAutoSave(true);
        settings.setEditorPublishReminder(true);
        settings.setPublishDefaultAudience("public");
        settings.setPublishShowProvenance(true);
        settings.setPublishHighlightRecentUpdates(true);
        settings.setCreatedAt(now);
        settings.setUpdatedAt(now);
        return workspaceSettingsRepository.save(settings);
    }

    private SettingsResponse toResponse(UserEntity user, WorkspaceSettingsEntity settings) {
        return new SettingsResponse(
                new SettingsResponse.Profile(
                        settings.getDisplayName(),
                        settings.getPublicTitle(),
                        settings.getSummary(),
                        settings.getPublicLocation()
                ),
                new SettingsResponse.Workbench(
                        settings.getDefaultPage(),
                        settings.isCompactMode(),
                        settings.isShowContextRibbon()
                ),
                new SettingsResponse.Editor(
                        settings.getEditorDefaultView(),
                        settings.isEditorAutoSave(),
                        settings.isEditorPublishReminder()
                ),
                new SettingsResponse.Publish(
                        settings.getPublishDefaultAudience(),
                        settings.isPublishShowProvenance(),
                        settings.isPublishHighlightRecentUpdates()
                ),
                new SettingsResponse.Security(
                        user.getEmail(),
                        "隐藏主人入口",
                        formatDurationLabel(sessionDuration)
                )
        );
    }

    private String formatDurationLabel(Duration duration) {
        if (duration.toHours() > 0 && duration.toMinutesPart() == 0) {
            return duration.toHours() + " 小时";
        }
        if (duration.toMinutes() > 0) {
            return duration.toMinutes() + " 分钟";
        }
        return duration.getSeconds() + " 秒";
    }
}
