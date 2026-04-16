package com.inkdesk.server.settings;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public record UpdateSettingsRequest(
        Profile profile,
        Workbench workbench,
        Editor editor,
        Publish publish
) {
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Profile(
            String displayName,
            String publicTitle,
            String summary,
            String publicLocation
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Workbench(
            String defaultPage,
            boolean compactMode,
            boolean showContextRibbon
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Editor(
            String defaultView,
            boolean autoSave,
            boolean publishReminder
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Publish(
            String defaultAudience,
            boolean showProvenance,
            boolean highlightRecentUpdates
    ) {
    }
}
