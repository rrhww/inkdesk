package com.inkdesk.server.knowledge.api;

import com.inkdesk.server.knowledge.service.KnowledgeQueryService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/public/articles")
public class PublicArticleController {

    private final KnowledgeQueryService knowledgeQueryService;

    public PublicArticleController(KnowledgeQueryService knowledgeQueryService) {
        this.knowledgeQueryService = knowledgeQueryService;
    }

    @GetMapping
    public List<PublicArticleSummaryResponse> getPublicArticles() {
        return knowledgeQueryService.getPublicArticles();
    }

    @GetMapping("/{slug}")
    public PublicArticleDetailResponse getPublicArticle(@PathVariable String slug) {
        return knowledgeQueryService.getPublicArticle(slug);
    }
}
