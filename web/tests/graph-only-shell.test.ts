import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

<<<<<<< HEAD
test("knowledge and task work surfaces are the active application routes", () => {
  for (const route of ["ask", "compile", "ingest", "raw", "runs", "skills"]) {
    assert.equal(existsSync(join(process.cwd(), "app", "app", route)), false, `${route} should be removed`);
  }
  const appPage = readFileSync(join(process.cwd(), "app", "app", "page.tsx"), "utf8");
  const appLayout = readFileSync(join(process.cwd(), "app", "app", "layout.tsx"), "utf8");
  assert.match(appPage, /redirect\(["']\/app\/wiki["']\)/);
  assert.equal(existsSync(join(process.cwd(), "app", "app", "health")), true);
  assert.equal(existsSync(join(process.cwd(), "app", "app", "tasks")), true);
=======
test("graph board remains primary and only the read-only run inspector is restored", () => {
  for (const route of ["ask", "compile", "health", "ingest", "raw", "skills"]) {
    assert.equal(existsSync(join(process.cwd(), "app", "app", route)), false, `${route} should be removed`);
  }
  assert.equal(existsSync(join(process.cwd(), "app", "app", "runs", "[runId]", "page.tsx")), true);
  const appPage = readFileSync(join(process.cwd(), "app", "app", "page.tsx"), "utf8");
  const appLayout = readFileSync(join(process.cwd(), "app", "app", "layout.tsx"), "utf8");
  assert.match(appPage, /redirect\("\/app\/wiki"\)/);
>>>>>>> origin/main
  assert.doesNotMatch(appLayout, /AppChrome|getResearchDashboard|getDevRuns/);
});
