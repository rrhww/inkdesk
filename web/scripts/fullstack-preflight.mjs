import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import net from "node:net";
import path from "node:path";

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

export function readEnvFileValue(filePath, key) {
  if (!existsSync(filePath)) {
    return undefined;
  }

  const lines = readFileSync(filePath, "utf8").split(/\r?\n/);

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line || line.startsWith("#")) {
      continue;
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex <= 0) {
      continue;
    }

    const currentKey = line.slice(0, separatorIndex).trim();
    if (currentKey !== key) {
      continue;
    }

    const value = line.slice(separatorIndex + 1).trim();
    return value.replace(/^['"]|['"]$/g, "");
  }

  return undefined;
}

export function normalizeApiBaseUrl(value) {
  if (!value) {
    return undefined;
  }

  return value.replace(/\/+$/, "");
}

export function toHealthUrl(apiBaseUrl) {
  const base = apiBaseUrl.endsWith("/api") ? apiBaseUrl.slice(0, -4) : apiBaseUrl;
  return `${base}/actuator/health`;
}

export function resolveApiBaseUrl({
  cwd = process.cwd(),
  env = process.env
} = {}) {
  const envFilePath = path.join(cwd, ".env.local");

  return normalizeApiBaseUrl(
    env.INKDESK_API_BASE_URL ??
      env.NEXT_PUBLIC_API_BASE_URL ??
      readEnvFileValue(envFilePath, "INKDESK_API_BASE_URL") ??
      readEnvFileValue(envFilePath, "NEXT_PUBLIC_API_BASE_URL")
  );
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function probeTcpPort(host, port, timeoutMs = 800) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let settled = false;

    const finish = (value) => {
      if (settled) {
        return;
      }

      settled = true;
      socket.destroy();
      resolve(value);
    };

    socket.setTimeout(timeoutMs);
    socket.once("connect", () => finish(true));
    socket.once("timeout", () => finish(false));
    socket.once("error", () => finish(false));
    socket.connect(port, host);
  });
}

export async function checkCommand(command, args = ["--version"]) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: "ignore"
    });

    child.once("error", () => resolve(false));
    child.once("exit", (code) => resolve(code === 0));
  });
}

export async function collectLocalDiagnostics(
  apiBaseUrl,
  {
    probeTcpPort: probeTcpPortImpl = probeTcpPort,
    checkCommand: checkCommandImpl = checkCommand
  } = {}
) {
  const url = new URL(apiBaseUrl);
  const backendHost = url.hostname;

  if (!LOCAL_HOSTS.has(backendHost)) {
    return {
      isLocal: false
    };
  }

  const backendPort = Number(url.port || (url.protocol === "https:" ? 443 : 80));
  const [backendReachable, postgresReachable, minioReachable, dockerAvailable] = await Promise.all([
    probeTcpPortImpl(backendHost, backendPort),
    probeTcpPortImpl("localhost", 5432),
    probeTcpPortImpl("localhost", 9000),
    checkCommandImpl(process.platform === "win32" ? "docker.exe" : "docker", ["version", "--format", "{{.Server.Version}}"])
  ]);

  return {
    isLocal: true,
    backendHost,
    backendPort,
    backendReachable,
    postgresReachable,
    minioReachable,
    dockerAvailable
  };
}

export function buildBackendUnavailableMessage({
  apiBaseUrl,
  healthUrl,
  lastStatus,
  lastError,
  diagnostics
}) {
  const lines = [`无法访问后端健康检查 ${healthUrl}。`];

  if (lastStatus) {
    lines.push(`最后一次健康检查返回 HTTP ${lastStatus}。`);
  }

  if (lastError) {
    lines.push(`最近一次错误：${lastError}`);
  }

  if (!diagnostics?.isLocal) {
    lines.push(`请确认 ${apiBaseUrl} 对应的后端已经启动并暴露健康检查。`);
    return lines.join(" ");
  }

  lines.push(`Spring Boot 还没有在 ${diagnostics.backendHost}:${diagnostics.backendPort} 提供健康检查。`);

  if (diagnostics.postgresReachable) {
    lines.push("PostgreSQL 已经就绪，更像是后端还没启动或仍在启动中。");
  } else {
    lines.push("PostgreSQL 也没有在 localhost:5432 监听，本地数据库大概率还没准备好。");
  }

  if (diagnostics.minioReachable === false && diagnostics.dockerAvailable) {
    lines.push("MinIO 也还没有在 localhost:9000 就绪，建议一起检查基础设施启动状态。");
  }

  if (!diagnostics.dockerAvailable) {
    lines.push("当前机器还没有可用的 docker 命令，无法按仓库默认方式启动 PostgreSQL + MinIO。");
  } else if (!diagnostics.postgresReachable || diagnostics.minioReachable === false) {
    lines.push("可以先运行 `docker compose --env-file infra/.env -f infra/docker-compose.yml up -d`，再用 `docker compose --env-file infra/.env -f infra/docker-compose.yml ps` 确认服务状态。");
  }

  if (diagnostics.postgresReachable && !diagnostics.backendReachable) {
    lines.push("然后启动后端：先进入 `server`，再执行 `.\\mvnw.cmd spring-boot:run -Dspring-boot.run.profiles=local`。");
  }

  return lines.join(" ");
}

export async function waitForBackendReady(
  apiBaseUrl,
  {
    timeoutMs = 60_000,
    intervalMs = 2_000,
    log = console.log
  } = {},
  {
    fetchImpl = fetch,
    probeTcpPort: probeTcpPortImpl = probeTcpPort,
    checkCommand: checkCommandImpl = checkCommand
  } = {}
) {
  const healthUrl = toHealthUrl(apiBaseUrl);
  const deadline = Date.now() + timeoutMs;
  let lastStatus;
  let lastError;
  let hasLoggedWait = false;

  while (Date.now() < deadline) {
    try {
      const response = await fetchImpl(healthUrl);

      if (response.ok) {
        return;
      }

      lastStatus = response.status;
      lastError = undefined;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }

    if (!hasLoggedWait && log) {
      log(`[inkdesk:e2e:fullstack] waiting for backend health at ${healthUrl} ...`);
      hasLoggedWait = true;
    }

    await sleep(intervalMs);
  }

  const diagnostics = await collectLocalDiagnostics(apiBaseUrl, {
    probeTcpPort: probeTcpPortImpl,
    checkCommand: checkCommandImpl
  });

  throw new Error(
    buildBackendUnavailableMessage({
      apiBaseUrl,
      healthUrl,
      lastStatus,
      lastError,
      diagnostics
    })
  );
}
