package com.inkdesk.server.settings;

import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkspaceSettingsRepository extends JpaRepository<WorkspaceSettingsEntity, String> {
}
