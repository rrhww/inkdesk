import { describe, expect, it } from "vitest";

import {
  buildBackendUnavailableMessage,
  collectLocalDiagnostics,
  normalizeApiBaseUrl,
  toHealthUrl
} from "@/scripts/fullstack-preflight.mjs";

describe("fullstack preflight helpers", () => {
  it("normalizes api base urls and derives the health endpoint", () => {
    expect(normalizeApiBaseUrl("http://localhost:8080/api/")).toBe("http://localhost:8080/api");
    expect(toHealthUrl("http://localhost:8080/api")).toBe("http://localhost:8080/actuator/health");
  });

  it("collects localhost diagnostics for backend, postgres, minio and docker", async () => {
    const diagnostics = await collectLocalDiagnostics("http://localhost:8080/api", {
      probeTcpPort: async (_host: string, port: number) => port === 5432 || port === 9000,
      checkCommand: async () => false
    });

    expect(diagnostics.isLocal).toBe(true);

    if (!diagnostics.isLocal) {
      throw new Error("Expected local diagnostics");
    }

    expect(diagnostics.backendPort).toBe(8080);
    expect(diagnostics.backendReachable).toBe(false);
    expect(diagnostics.postgresReachable).toBe(true);
    expect(diagnostics.minioReachable).toBe(true);
    expect(diagnostics.dockerAvailable).toBe(false);
  });

  it("builds a docker and postgres hint when the local backend is unavailable", () => {
    const message = buildBackendUnavailableMessage({
      apiBaseUrl: "http://localhost:8080/api",
      healthUrl: "http://localhost:8080/actuator/health",
      lastError: "fetch failed",
      diagnostics: {
        isLocal: true,
        backendHost: "localhost",
        backendPort: 8080,
        backendReachable: false,
        postgresReachable: false,
        minioReachable: false,
        dockerAvailable: false
      }
    });

    expect(message).toContain("无法访问后端健康检查");
    expect(message).toContain("Python 后端还没有在 localhost:8080 提供健康检查");
    expect(message).toContain("PostgreSQL 也没有在 localhost:5432 监听");
    expect(message).toContain("当前机器还没有可用的 docker 命令");
  });

  it("builds a backend startup hint when postgres is ready but the python backend is not", () => {
    const message = buildBackendUnavailableMessage({
      apiBaseUrl: "http://localhost:8080/api",
      healthUrl: "http://localhost:8080/actuator/health",
      lastError: "connect ECONNREFUSED",
      diagnostics: {
        isLocal: true,
        backendHost: "localhost",
        backendPort: 8080,
        backendReachable: false,
        postgresReachable: true,
        minioReachable: true,
        dockerAvailable: true
      }
    });

    expect(message).toContain("PostgreSQL 已经就绪");
    expect(message).toContain("python -m uvicorn inkvault_server.main:app --host 0.0.0.0 --port 8080");
  });
});
