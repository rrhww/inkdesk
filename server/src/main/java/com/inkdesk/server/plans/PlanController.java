package com.inkdesk.server.plans;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/admin/plans")
public class PlanController {

    private final PlanQueryService planQueryService;
    private final PlanCommandService planCommandService;

    public PlanController(PlanQueryService planQueryService, PlanCommandService planCommandService) {
        this.planQueryService = planQueryService;
        this.planCommandService = planCommandService;
    }

    @GetMapping
    public List<PlanListItemResponse> getPlans() {
        return planQueryService.getPlans();
    }

    @PostMapping
    public ResponseEntity<PlanListItemResponse> createPlan(@RequestBody PlanUpsertRequest request) {
        return ResponseEntity.status(201).body(planCommandService.createPlan(request));
    }

    @PatchMapping("/{id}")
    public PlanListItemResponse updatePlan(@PathVariable String id, @RequestBody PlanUpsertRequest request) {
        return planCommandService.updatePlan(id, request);
    }
}
