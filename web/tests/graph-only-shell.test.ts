import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

test("graph board is the only application route", () => {
  for (const route of ["ask", "compile", "health", "ingest", "raw", "runs", "skills"]) {
    assert.equal(existsSync(join(process.cwd(), "app", "app", route)), false, `${route} should be removed`);
  }
  const appPage = readFileSync(join(process.cwd(), "app", "app", "page.tsx"), "utf8");
  const appLayout = readFileSync(join(process.cwd(), "app", "app", "layout.tsx"), "utf8");
  assert.match(appPage, /redirect\("\/app\/wiki"\)/);
  assert.doesNotMatch(appLayout, /AppChrome|getResearchDashboard|getDevRuns/);
});
