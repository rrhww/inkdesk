package com.inkdesk.server.auth.mock;

public record AuthMeResponse(
        String userId,
        String username,
        String workspaceId,
        String workspaceName,
        String workspaceSlug
) {
}
