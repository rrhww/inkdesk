package com.inkdesk.server.auth.mock;

import com.inkdesk.server.knowledge.persistence.UserEntity;
import com.inkdesk.server.knowledge.persistence.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Optional;

@Service
public class OwnerSessionService {

    private static final Base64.Encoder URL_ENCODER = Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder URL_DECODER = Base64.getUrlDecoder();
    private static final String HMAC_ALGORITHM = "HmacSHA256";

    private final UserRepository userRepository;
    private final Clock clock;
    private final Duration sessionDuration;
    private final byte[] signingKey;
    private final boolean allowLegacyOwnerCookie;

    public OwnerSessionService(
            UserRepository userRepository,
            @Value("${inkdesk.auth.secret}") String secret,
            @Value("${inkdesk.auth.session-duration:PT8H}") Duration sessionDuration,
            @Value("${inkdesk.auth.allow-legacy-owner-cookie:false}") boolean allowLegacyOwnerCookie
    ) {
        this.userRepository = userRepository;
        this.clock = Clock.systemUTC();
        this.sessionDuration = sessionDuration;
        this.signingKey = secret.getBytes(StandardCharsets.UTF_8);
        this.allowLegacyOwnerCookie = allowLegacyOwnerCookie;
    }

    public String createSessionToken(UserEntity user) {
        long expiresAt = Instant.now(clock).plus(sessionDuration).toEpochMilli();
        long sessionVersion = user.getUpdatedAt().toEpochMilli();
        String payload = user.getId() + ":" + expiresAt + ":" + sessionVersion;
        String signature = encode(sign(payload));
        return encode(payload.getBytes(StandardCharsets.UTF_8)) + "." + signature;
    }

    public Optional<VerifiedOwnerSession> verifySessionToken(String token) {
        if (allowLegacyOwnerCookie && MockOwnerAuthenticationFilter.OWNER_COOKIE_VALUE.equals(token)) {
            return userRepository.findByUsername("owner")
                    .map(user -> new VerifiedOwnerSession(user.getId(), user.getUsername()));
        }

        String[] parts = token.split("\\.");
        if (parts.length != 2) {
            return Optional.empty();
        }

        byte[] payloadBytes;
        byte[] providedSignature;
        try {
            payloadBytes = URL_DECODER.decode(parts[0]);
            providedSignature = URL_DECODER.decode(parts[1]);
        } catch (IllegalArgumentException exception) {
            return Optional.empty();
        }

        byte[] expectedSignature = sign(new String(payloadBytes, StandardCharsets.UTF_8));
        if (!MessageDigest.isEqual(expectedSignature, providedSignature)) {
            return Optional.empty();
        }

        String[] payload = new String(payloadBytes, StandardCharsets.UTF_8).split(":");
        if (payload.length != 3) {
            return Optional.empty();
        }

        long expiresAt;
        long sessionVersion;
        try {
            expiresAt = Long.parseLong(payload[1]);
            sessionVersion = Long.parseLong(payload[2]);
        } catch (NumberFormatException exception) {
            return Optional.empty();
        }

        if (Instant.now(clock).toEpochMilli() > expiresAt) {
            return Optional.empty();
        }

        return userRepository.findById(payload[0])
                .filter(user -> "ACTIVE".equalsIgnoreCase(user.getStatus()))
                .filter(user -> user.getUpdatedAt().toEpochMilli() == sessionVersion)
                .map(user -> new VerifiedOwnerSession(user.getId(), user.getUsername()));
    }

    public void invalidateSession(String username) {
        userRepository.findByUsername(username).ifPresent(user -> {
            user.setUpdatedAt(Instant.now(clock));
            userRepository.save(user);
        });
    }

    private byte[] sign(String payload) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(signingKey, HMAC_ALGORITHM));
            return mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to sign owner session token.", exception);
        }
    }

    private String encode(byte[] bytes) {
        return URL_ENCODER.encodeToString(bytes);
    }
}
