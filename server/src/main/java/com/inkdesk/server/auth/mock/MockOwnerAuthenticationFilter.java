package com.inkdesk.server.auth.mock;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.util.matcher.AntPathRequestMatcher;
import org.springframework.security.web.util.matcher.OrRequestMatcher;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Arrays;
import java.util.Optional;

@Component
public class MockOwnerAuthenticationFilter extends OncePerRequestFilter {

    public static final String OWNER_COOKIE_NAME = "inkdesk_owner_session";
    public static final String OWNER_COOKIE_VALUE = "owner";

    private final RequestMatcher protectedMatcher = new OrRequestMatcher(
            new AntPathRequestMatcher("/api/admin/**"),
            new AntPathRequestMatcher("/api/auth/me"),
            new AntPathRequestMatcher("/api/auth/logout")
    );

    private final OwnerSessionService ownerSessionService;

    public MockOwnerAuthenticationFilter(OwnerSessionService ownerSessionService) {
        this.ownerSessionService = ownerSessionService;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !protectedMatcher.matches(request);
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() == null) {
            findOwnerSessionToken(request)
                    .flatMap(ownerSessionService::verifySessionToken)
                    .ifPresent(session -> {
                        MockOwnerPrincipal principal = new MockOwnerPrincipal(session.username());
                        UsernamePasswordAuthenticationToken authentication =
                                UsernamePasswordAuthenticationToken.authenticated(principal, null, principal.getAuthorities());
                        SecurityContextHolder.getContext().setAuthentication(authentication);
                    });
        }

        filterChain.doFilter(request, response);
    }

    private Optional<String> findOwnerSessionToken(HttpServletRequest request) {
        Cookie[] cookies = request.getCookies();

        if (cookies != null) {
            Optional<String> matchedCookie = Arrays.stream(cookies)
                    .filter(cookie -> OWNER_COOKIE_NAME.equals(cookie.getName()))
                    .map(Cookie::getValue)
                    .findFirst();
            if (matchedCookie.isPresent()) {
                return matchedCookie;
            }
        }

        return Optional.ofNullable(request.getHeader("Cookie"))
                .stream()
                .flatMap(header -> Arrays.stream(header.split(";")))
                .map(String::trim)
                .filter(cookie -> cookie.startsWith(OWNER_COOKIE_NAME + "="))
                .map(cookie -> cookie.substring((OWNER_COOKIE_NAME + "=").length()))
                .findFirst();
    }
}
