package com.inkdesk.server.settings;

public record SettingsResponse(
        Profile profile,
        Workbench workbench,
        Editor editor,
        Publish publish,
        Security security
) {
    public record Profile(
            String displayName,
            String publicTitle,
            String summary,
            String publicLocation
    ) {
    }

    public record Workbench(
            String defaultPage,
            boolean compactMode,
            boolean showContextRibbon
    ) {
    }

    public record Editor(
            String defaultView,
            boolean autoSave,
            boolean publishReminder
    ) {
    }

    public record Publish(
            String defaultAudience,
            boolean showProvenance,
            boolean highlightRecentUpdates
    ) {
    }

    public record Security(
            String ownerEmail,
            String sessionMode,
            String sessionDurationLabel
    ) {
    }
}
