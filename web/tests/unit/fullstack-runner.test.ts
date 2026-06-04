import path from "node:path";

import { describe, expect, it } from "vitest";

import { buildPlaywrightCommand } from "@/scripts/run-fullstack-e2e.mjs";

describe("fullstack e2e runner", () => {
  it("uses the local playwright cli through the current node executable", () => {
    const command = buildPlaywrightCommand({
      cwd: "E:/dev/projects/inkdesk/web"
    });

    expect(command.command).toBe(process.execPath);
    expect(command.args).toEqual([
      path.join("E:/dev/projects/inkdesk/web", "node_modules", "playwright", "cli.js"),
      "test",
      "tests/e2e/local-fullstack.spec.ts"
    ]);
  });
});
