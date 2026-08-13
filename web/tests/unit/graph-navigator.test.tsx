import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GraphNavigator } from "@/components/workbench/graph-navigator";
import type { GraphSnapshotNode } from "@/lib/server-api";

const documents: GraphSnapshotNode[] = [
  {
    id: "prd",
    label: "Interview PRD",
    kind: "document",
    path: "docs/prd.md",
    source: "repo",
    status: "stable",
    summary: "",
    classification: {
      stage: "requirements",
      domain: "product",
      category: "prd",
      importance: "core",
      visibility: "primary",
      origin: "rule"
    }
  },
  {
    id: "solution",
    label: "Interview Solution",
    kind: "solution",
    path: "docs/solution.md",
    source: "repo",
    status: "draft",
    summary: "",
    classification: {
      stage: "design",
      domain: "architecture",
      category: "tech-solution",
      importance: "core",
      visibility: "primary",
      origin: "rule"
    }
  }
];

describe("GraphNavigator", () => {
  it("moves through stage, domain, and document levels with explicit controls", async () => {
    const user = userEvent.setup();
    const onStageChange = vi.fn();
    const onDomainChange = vi.fn();
    const onDocumentOpen = vi.fn();
    const { rerender } = render(
      <GraphNavigator
        documents={documents}
        stage={null}
        domain={null}
        onStageChange={onStageChange}
        onDomainChange={onDomainChange}
        onDocumentOpen={onDocumentOpen}
      />
    );

    await user.click(screen.getByRole("button", { name: /方案设计/ }));
    expect(onStageChange).toHaveBeenCalledWith("design");

    rerender(
      <GraphNavigator
        documents={documents}
        stage="design"
        domain={null}
        onStageChange={onStageChange}
        onDomainChange={onDomainChange}
        onDocumentOpen={onDocumentOpen}
      />
    );
    await user.click(screen.getByRole("button", { name: /Architecture/ }));
    expect(onDomainChange).toHaveBeenCalledWith("architecture");

    rerender(
      <GraphNavigator
        documents={documents}
        stage="design"
        domain="architecture"
        onStageChange={onStageChange}
        onDomainChange={onDomainChange}
        onDocumentOpen={onDocumentOpen}
      />
    );
    await user.click(screen.getByRole("button", { name: /Interview Solution/ }));
    expect(onDocumentOpen).toHaveBeenCalledWith(expect.objectContaining({ id: "solution" }));
  });
});
