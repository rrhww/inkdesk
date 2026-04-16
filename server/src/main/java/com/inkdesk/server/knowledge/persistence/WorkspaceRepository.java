package com.inkdesk.server.knowledge.persistence;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface WorkspaceRepository extends JpaRepository<WorkspaceEntity, String> {

    Optional<WorkspaceEntity> findByOwnerUserId(String ownerUserId);

    Optional<WorkspaceEntity> findBySlug(String slug);
}
