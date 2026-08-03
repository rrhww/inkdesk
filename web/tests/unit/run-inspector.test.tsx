import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RunInspector } from "@/components/workbench/run-inspector";
import { ServerAPI, type HarnessRun } from "@/lib/server-api";

const run: HarnessRun = {
  id: "run-example",
  capabilityId: "harness-audit",
  executor: "claude",
  inputs: { target: "repository", depth: "quick" },
  status: "succeeded",
  sourceHead: "0123456789abcdef",
  createdAt: "2026-07-30T00:00:00Z",
  updatedAt: "2026-07-30T00:01:00Z",
  stageStates: { preflight: "succeeded", "collect-evidence": "succeeded" },
  reportPath: "/vault/wiki/generated/repo-harness-audit.md",
  evidence: {
    sessionEvidenceStatus: "unavailable",
    envelopes: {
      projectHarness: { status: "available", summaryFacts: ["Collected project guidance."], evidence: [{}] }
    }
  },
  findings: {
    supportTrack: "fixture",
    dimensionScores: {
      "Task Understanding": 3,
      "Controlled Execution": 2,
      "Change Validation": 2,
      "Reliable Delivery": 1,
      "Learning Capture": 1
    },
    findings: [
      {
        id: "F-001",
        dimension: "Reliable Delivery",
        severity: "high",
        confidence: "high",
        title: "No automated release gate",
        consequence: "An unverified release can be published.",
        causeChain: "No required CI status check.",
        owner: "delivery",
        evidence: ["E-1"],
        expectedArtifact: "CI workflow",
        repairScope: ".github/workflows",
        verifiers: ["required check passes"],
        status: "open"
      }
    ]
  }
};

describe("RunInspector", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders persisted stages, evidence, scores, and findings", async () => {
    vi.spyOn(ServerAPI, "fetchHarnessRun").mockResolvedValue(run);
    vi.spyOn(ServerAPI, "fetchHarnessPermissions").mockResolvedValue([]);
    vi.spyOn(ServerAPI, "subscribeToRunEvents").mockImplementation((_id, _event, status) => {
      status("connected");
      return () => undefined;
    });

    render(<RunInspector runId="run-example" />);

    await waitFor(() => expect(screen.getByText("No automated release gate")).toBeInTheDocument());
    expect(screen.getByText("claude")).toBeInTheDocument();
    expect(screen.getByText("Collected project guidance.")).toBeInTheDocument();
    expect(screen.getByText("3", { selector: "div" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open report/i })).toBeInTheDocument();
  });

  it("renders and resolves a pending read-only approval", async () => {
    vi.spyOn(ServerAPI, "fetchHarnessRun").mockResolvedValue({ ...run, status: "running" });
    vi.spyOn(ServerAPI, "fetchHarnessPermissions").mockResolvedValue([
      {
        id: "perm-1",
        runId: run.id,
        stageId: "specialist-structure",
        sessionId: "session-1",
        toolUseId: "tool-1",
        tool: "Bash",
        inputPreview: { command: "ls" },
        status: "pending",
        createdAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 90_000).toISOString()
      }
    ]);
    const decide = vi.spyOn(ServerAPI, "decideHarnessPermission").mockResolvedValue({} as never);
    vi.spyOn(ServerAPI, "subscribeToRunEvents").mockImplementation((_id, _event, status) => {
      status("connected");
      return () => undefined;
    });

    render(<RunInspector runId="run-example" />);

    const allow = await screen.findByRole("button", { name: /allow once/i });
    allow.click();
    await waitFor(() => expect(decide).toHaveBeenCalledWith("run-example", "perm-1", "allow_once"));
  });
});
