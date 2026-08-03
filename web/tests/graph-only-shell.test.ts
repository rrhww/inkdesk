import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

test("graph board remains primary and only the read-only run inspector is restored", () => {
  for (const route of ["ask", "compile", "health", "ingest", "raw", "skills"]) {
    assert.equal(existsSync(join(process.cwd(), "app", "app", route)), false, `${route} should be removed`);
  }
  assert.equal(existsSync(join(process.cwd(), "app", "app", "runs", "[runId]", "page.tsx")), true);
  const appPage = readFileSync(join(process.cwd(), "app", "app", "page.tsx"), "utf8");
  const appLayout = readFileSync(join(process.cwd(), "app", "app", "layout.tsx"), "utf8");
  assert.match(appPage, /redirect\("\/app\/wiki"\)/);
  assert.doesNotMatch(appLayout, /AppChrome|getResearchDashboard|getDevRuns/);
});
