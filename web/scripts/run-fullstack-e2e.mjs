import { spawn } from "node:child_process";
import path from "node:path";
import { resolveApiBaseUrl, waitForBackendReady } from "./fullstack-preflight.mjs";

export function buildPlaywrightCommand({
  cwd = process.cwd()
} = {}) {
  return {
    command: process.execPath,
    args: [
      path.join(cwd, "node_modules", "playwright", "cli.js"),
      "test",
      "tests/e2e/local-fullstack.spec.ts"
    ]
  };
}

async function main() {
  const apiBaseUrl = resolveApiBaseUrl();

  if (!apiBaseUrl) {
    throw new Error("未找到 API 地址。请先配置 web/.env.local 中的 INKDESK_API_BASE_URL 或 NEXT_PUBLIC_API_BASE_URL。");
  }

  const timeoutMs = Number(process.env.INKDESK_E2E_BACKEND_TIMEOUT_MS ?? 60_000);
  await waitForBackendReady(apiBaseUrl, {
    timeoutMs,
    intervalMs: 2_000
  });

  const { command, args } = buildPlaywrightCommand();
  const child = spawn(command, args, {
    stdio: "inherit",
    env: {
      ...process.env,
      INKDESK_E2E_FULLSTACK: "1"
    }
  });

  child.on("error", (error) => {
    console.error(`[inkdesk:e2e:fullstack] ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }

    process.exit(code ?? 1);
  });
}

main().catch((error) => {
  console.error(`[inkdesk:e2e:fullstack] ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
