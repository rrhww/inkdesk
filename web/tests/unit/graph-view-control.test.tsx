import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GraphViewControl } from "@/components/workbench/graph-view-control";

describe("GraphViewControl", () => {
  it("makes the hierarchical flow primary and keeps the raw graph behind an advanced control", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<GraphViewControl value="flow" onChange={onChange} disabled={false} />);

    expect(screen.getByRole("group", { name: "Graph view" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Research flow" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Local relations" }));
    expect(onChange).toHaveBeenCalledWith("relations");

    await user.click(screen.getByText("ADVANCED"));
    await user.click(screen.getByRole("button", { name: "Raw graph" }));
    expect(onChange).toHaveBeenCalledWith("raw");
  });
});
