import { existsSync, readdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

function resolveChromiumExecutablePath() {
  const browserRoot = path.join(os.homedir(), "AppData", "Local", "ms-playwright");

  if (!existsSync(browserRoot)) {
    return undefined;
  }

  const chromiumDir = readdirSync(browserRoot, {
    withFileTypes: true
  })
    .filter((entry) => entry.isDirectory() && entry.name.startsWith("chromium-"))
    .sort((left, right) => left.name.localeCompare(right.name))
    .at(-1);

  if (!chromiumDir) {
    return undefined;
  }

  const executablePath = path.join(browserRoot, chromiumDir.name, "chrome-win64", "chrome.exe");

  return existsSync(executablePath) ? executablePath : undefined;
}

const chromiumExecutablePath = resolveChromiumExecutablePath();

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3301",
    trace: "on-first-retry",
    ...(chromiumExecutablePath
      ? {
          launchOptions: {
            executablePath: chromiumExecutablePath
          }
        }
      : {})
  },
  webServer: {
    command: "npm run build && npm run start -- --port 3301",
    port: 3301,
    reuseExistingServer: true,
    timeout: 240_000
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"]
      }
    }
  ]
});
