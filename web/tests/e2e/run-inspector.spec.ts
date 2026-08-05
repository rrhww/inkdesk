import { expect, test } from "@playwright/test";

test("shows a persisted harness audit run", async ({ page }) => {
  const runId = "run-browser-smoke";
  await page.route(`**/api/runs/${runId}`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: runId,
        capabilityId: "harness-audit",
        executor: "claude",
        inputs: { target: "repository", depth: "quick" },
        status: "succeeded",
        sourceHead: "40011c1e98374c4",
        createdAt: "2026-07-30T00:00:00Z",
        updatedAt: "2026-07-30T00:01:00Z",
        stageStates: Object.fromEntries([
          "preflight", "collect-evidence", "specialist-structure", "specialist-testing",
          "specialist-security", "lead-reconcile", "validate-findings", "write-report", "graph-refresh"
        ].map((id) => [id, "succeeded"])),
        reportPath: "/vault/wiki/generated/repo-harness-audit.md",
        evidence: {
          sessionEvidenceStatus: "unavailable",
          envelopes: { projectHarness: { status: "available", summaryFacts: ["Evidence frozen."], evidence: [{}] } }
        },
        findings: {
          supportTrack: "smoke",
          dimensionScores: {
            "Task Understanding": 3, "Controlled Execution": 3, "Change Validation": 2,
            "Reliable Delivery": 2, "Learning Capture": 1
          },
          findings: [{
            id: "F-001", dimension: "Reliable Delivery", severity: "high", confidence: "high",
            title: "Release gate is not enforced", consequence: "Unverified delivery remains possible.",
            causeChain: "No required status check.", owner: "delivery", evidence: ["E-1"],
            expectedArtifact: "CI rule", repairScope: ".github", verifiers: ["required check"], status: "open"
          }]
        }
      })
    });
  });
  await page.route(`**/api/runs/${runId}/events`, async (route) => {
    await route.fulfill({
      contentType: "text/event-stream",
      body: [
        "id: 1",
        "event: executor.tool.completed",
        "data: {\"sequence\":1,\"type\":\"executor.tool.completed\",\"timestamp\":\"now\",\"data\":{\"stageId\":\"specialist-testing\",\"tool\":\"Read\",\"evidenceId\":\"E-A-browser\"}}",
        "",
        "id: 2",
        "event: stream.end",
        "data: {\"sequence\":2,\"type\":\"stream.end\",\"timestamp\":\"now\",\"data\":{\"status\":\"succeeded\"}}",
        "",
        ""
      ].join("\n")
    });
  });
  await page.route(`**/api/runs/${runId}/permissions**`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: "[]" });
  });

  await page.goto(`/app/runs/${runId}`);
  await expect(page.getByRole("heading", { name: runId })).toBeVisible();
  await expect(page.getByText("Release gate is not enforced")).toBeVisible();
  await expect(page.getByText("Evidence frozen.")).toBeVisible();
  await expect(page.getByText("Graph refresh")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent tool activity" })).toBeVisible();
  await expect(page.getByText("Read", { exact: true })).toBeVisible();
});

test("resolves a pending read-only approval once", async ({ page }) => {
  const runId = "run-browser-permission";
  let pending = true;
  const run = {
    id: runId,
    capabilityId: "harness-audit",
    executor: "claude",
    inputs: { target: "repository", depth: "quick" },
    status: "running",
    sourceHead: "40011c1e98374c4",
    createdAt: "2026-07-30T00:00:00Z",
    updatedAt: "2026-07-30T00:01:00Z",
    stageStates: { preflight: "succeeded" },
    findings: null,
    evidence: null
  };
  await page.route(`**/api/runs/${runId}`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(run) });
  });
  await page.route(`**/api/runs/${runId}/events`, async (route) => {
    await route.fulfill({ contentType: "text/event-stream", body: "event: stream.end\ndata: {\"sequence\":1,\"type\":\"stream.end\",\"timestamp\":\"now\",\"data\":{\"status\":\"running\"}}\n\n" });
  });
  await page.route(`**/api/runs/${runId}/permissions**`, async (route) => {
    if (route.request().method() === "POST") {
      pending = false;
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ id: "perm-browser", status: "allowed" })
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(pending ? [{
        id: "perm-browser",
        runId,
        stageId: "specialist-testing",
        sessionId: "session-browser",
        toolUseId: "tool-browser",
        tool: "Bash",
        inputPreview: { command: "git log --oneline" },
        status: "pending",
        createdAt: "2026-07-30T00:00:00Z",
        expiresAt: "2099-07-30T00:01:30Z"
      }] : [])
    });
  });

  await page.goto(`/app/runs/${runId}`);
  await expect(page.getByRole("heading", { name: runId })).toBeVisible();
  await expect(page.getByText("specialist-testing")).toBeVisible();
  await page.getByRole("button", { name: "Allow once" }).click();
  await expect(page.getByRole("button", { name: "Allow once" })).toHaveCount(0);
});
