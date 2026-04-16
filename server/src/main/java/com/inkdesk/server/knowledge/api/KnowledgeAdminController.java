package com.inkdesk.server.knowledge.api;

import com.inkdesk.server.knowledge.service.KnowledgeQueryService;
import com.inkdesk.server.knowledge.service.KnowledgeCommandService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/admin/notes")
public class KnowledgeAdminController {

    private final KnowledgeQueryService knowledgeQueryService;
    private final KnowledgeCommandService knowledgeCommandService;

    public KnowledgeAdminController(
            KnowledgeQueryService knowledgeQueryService,
            KnowledgeCommandService knowledgeCommandService
    ) {
        this.knowledgeQueryService = knowledgeQueryService;
        this.knowledgeCommandService = knowledgeCommandService;
    }

    @GetMapping("/tree")
    public List<AdminNoteTreeItemResponse> getAdminTree() {
        return knowledgeQueryService.getAdminNoteTree();
    }

    @PostMapping
    public ResponseEntity<AdminNoteDetailResponse> createNote(@RequestBody NoteUpsertRequest request) {
        return ResponseEntity.status(201).body(knowledgeCommandService.createNote(request));
    }

    @GetMapping("/{id}")
    public AdminNoteDetailResponse getAdminNote(@PathVariable String id) {
        return knowledgeQueryService.getAdminNoteDetail(id);
    }

    @PatchMapping("/{id}")
    public AdminNoteDetailResponse updateNote(@PathVariable String id, @RequestBody NoteUpsertRequest request) {
        return knowledgeCommandService.updateNote(id, request);
    }

    @PostMapping("/{id}/publish")
    public AdminNoteDetailResponse publishNote(@PathVariable String id) {
        return knowledgeCommandService.publishNote(id);
    }

    @PostMapping("/{id}/unpublish")
    public AdminNoteDetailResponse unpublishNote(@PathVariable String id) {
        return knowledgeCommandService.unpublishNote(id);
    }
}
