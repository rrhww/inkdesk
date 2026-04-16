package com.inkdesk.server.knowledge.persistence;

import org.springframework.data.jpa.repository.JpaRepository;

public interface PublicationRepository extends JpaRepository<PublicationEntity, String> {

    boolean existsBySlug(String slug);
}
