package com.inkdesk.server.home;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/home")
public class HomeController {

    private final HomeQueryService homeQueryService;

    public HomeController(HomeQueryService homeQueryService) {
        this.homeQueryService = homeQueryService;
    }

    @GetMapping
    public AdminHomeResponse getHomeSnapshot() {
        return homeQueryService.getHomeSnapshot();
    }
}
