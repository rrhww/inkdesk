package com.inkdesk.server.knowledge.persistence;

import com.inkdesk.server.knowledge.model.NodeType;
import com.inkdesk.server.knowledge.model.PublicationStatus;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface ContentNodeRepository extends JpaRepository<ContentNodeEntity, String> {

    @EntityGraph(attributePaths = {"parent", "noteDocument", "tags", "publication"})
    @Query("select distinct node from ContentNodeEntity node where node.workspace.slug = :workspaceSlug")
    List<ContentNodeEntity> findTreeByWorkspaceSlugWithRelations(String workspaceSlug);

    @EntityGraph(attributePaths = {"parent", "noteDocument", "tags", "publication"})
    @Query("select distinct node from ContentNodeEntity node where node.id = :id and node.type = :type")
    Optional<ContentNodeEntity> findByIdAndTypeWithRelations(String id, NodeType type);

    @Query("""
            select coalesce(max(node.sortOrder), 0)
            from ContentNodeEntity node
            where node.workspace.id = :workspaceId
              and ((:parentId is null and node.parent is null) or node.parent.id = :parentId)
            """)
    Integer findMaxSortOrderByWorkspaceAndParentId(String workspaceId, String parentId);

    @EntityGraph(attributePaths = {"parent", "noteDocument", "tags", "publication"})
    @Query("""
            select distinct node
            from ContentNodeEntity node
            join node.publication publication
            where publication.status = :status
            """)
    List<ContentNodeEntity> findAllByPublicationStatusWithRelations(PublicationStatus status);

    @EntityGraph(attributePaths = {"parent", "noteDocument", "tags", "publication"})
    @Query("""
            select distinct node
            from ContentNodeEntity node
            join node.publication publication
            where publication.slug = :slug and publication.status = :status
            """)
    Optional<ContentNodeEntity> findByPublicationSlugAndStatusWithRelations(String slug, PublicationStatus status);

    default Optional<ContentNodeEntity> findNoteByIdWithRelations(String id) {
        return findByIdAndTypeWithRelations(id, NodeType.NOTE);
    }

    default List<ContentNodeEntity> findPublishedNotesWithRelations() {
        return findAllByPublicationStatusWithRelations(PublicationStatus.PUBLISHED);
    }
}
