import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GraphScopeControl } from "@/components/workbench/graph-scope-control";

describe("GraphScopeControl", () => {
  it("exposes all scopes as an accessible segmented control", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<GraphScopeControl value="all" onChange={onChange} disabled={false} />);

    const group = screen.getByRole("group", { name: "Graph scope" });
    const all = screen.getByRole("button", { name: "All nodes" });
    const vault = screen.getByRole("button", { name: "Vault nodes" });
    const repo = screen.getByRole("button", { name: "Repository nodes" });

    expect(group).toContainElement(all);
    expect(all).toHaveAttribute("aria-pressed", "true");
    expect(vault).toHaveAttribute("aria-pressed", "false");
    expect(repo).toHaveAttribute("aria-pressed", "false");

    await user.click(vault);
    expect(onChange).toHaveBeenCalledWith("vault");
  });
});
