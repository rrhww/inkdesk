import React from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DevRun, DevRunSummary } from "@/lib/types";

const push = vi.fn();
const getDevRuns = vi.fn();
const getVaultHealth = vi.fn();
const createDevRun = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/research", () => ({
  getDevRuns: (...args: unknown[]) => getDevRuns(...args),
  getVaultHealth: (...args: unknown[]) => getVaultHealth(...args),
  createDevRun: (...args: unknown[]) => createDevRun(...args),
}));

import { DevRunConsole } from "@/components/workbench/dev-run-console";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("DevRunConsole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getVaultHealth.mockResolvedValue(null);
  });

  it("keeps a newly created run when an older initial-list response arrives later", async () => {
    const initialRuns = deferred<DevRunSummary[]>();
    getDevRuns.mockReturnValue(initialRuns.promise);

    const createdRun: DevRun = {
      id: "run-new",
      workspaceId: "workspace-inkdesk",
      type: "PRD",
      title: "竞态回归任务",
      goal: "旧列表不能覆盖新任务",
      status: "active",
      currentStage: "context",
      stageStatus: "pending",
      stages: [],
      events: [],
      createdAt: "2026-06-21T12:00:00Z",
    };
    createDevRun.mockResolvedValue(createdRun);

    render(<DevRunConsole />);
    fireEvent.click(screen.getByRole("button", { name: /新建任务/ }));
    fireEvent.change(screen.getByPlaceholderText("任务标题"), { target: { value: createdRun.title } });
    fireEvent.change(screen.getByPlaceholderText("任务目标"), { target: { value: createdRun.goal } });
    fireEvent.click(screen.getByRole("button", { name: /^创建$/ }));

    await waitFor(() => expect(createDevRun).toHaveBeenCalledOnce());
    initialRuns.resolve([]);

    expect(await screen.findByRole("heading", { name: createdRun.title })).toBeInTheDocument();
  });
});
