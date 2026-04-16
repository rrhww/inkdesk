package com.inkdesk.server.auth.mock;

import com.inkdesk.server.common.exception.ResourceNotFoundException;
import com.inkdesk.server.knowledge.persistence.UserRepository;
import com.inkdesk.server.knowledge.persistence.WorkspaceRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final WorkspaceRepository workspaceRepository;
    private final PasswordEncoder passwordEncoder;
    private final OwnerSessionService ownerSessionService;

    public AuthService(
            UserRepository userRepository,
            WorkspaceRepository workspaceRepository,
            PasswordEncoder passwordEncoder,
            OwnerSessionService ownerSessionService
    ) {
        this.userRepository = userRepository;
        this.workspaceRepository = workspaceRepository;
        this.passwordEncoder = passwordEncoder;
        this.ownerSessionService = ownerSessionService;
    }

    @Transactional(readOnly = true)
    public AuthLoginResponse login(AuthLoginRequest request) {
        var user = userRepository.findByEmail(request.email())
                .filter(candidate -> "ACTIVE".equalsIgnoreCase(candidate.getStatus()))
                .filter(candidate -> passwordEncoder.matches(request.password(), candidate.getPasswordHash()))
                .orElseThrow(InvalidCredentialsException::new);

        return new AuthLoginResponse(ownerSessionService.createSessionToken(user));
    }

    @Transactional
    public void logout(String username) {
        ownerSessionService.invalidateSession(username);
    }

    @Transactional(readOnly = true)
    public AuthMeResponse getCurrentOwner(String username) {
        var user = userRepository.findByUsername(username)
                .orElseThrow(() -> new ResourceNotFoundException("Owner profile not found for username: " + username));
        var workspace = workspaceRepository.findByOwnerUserId(user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Workspace not found for owner: " + user.getId()));

        return new AuthMeResponse(
                user.getId(),
                user.getUsername(),
                workspace.getId(),
                workspace.getName(),
                workspace.getSlug()
        );
    }
}
