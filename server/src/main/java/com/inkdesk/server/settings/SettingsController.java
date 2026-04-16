package com.inkdesk.server.settings;

import com.inkdesk.server.auth.mock.MockOwnerPrincipal;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/settings")
public class SettingsController {

    private final SettingsService settingsService;

    public SettingsController(SettingsService settingsService) {
        this.settingsService = settingsService;
    }

    @GetMapping
    public SettingsResponse getSettings(@AuthenticationPrincipal MockOwnerPrincipal principal) {
        return settingsService.getSettings(principal.getUsername());
    }

    @PatchMapping
    public SettingsResponse updateSettings(
            @AuthenticationPrincipal MockOwnerPrincipal principal,
            @RequestBody UpdateSettingsRequest request
    ) {
        return settingsService.updateSettings(principal.getUsername(), request);
    }
}
