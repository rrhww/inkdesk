import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GraphViewControl } from "@/components/workbench/graph-view-control";

describe("GraphViewControl", () => {
  it("keeps presentation modes separate from graph source scopes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<GraphViewControl value="global" onChange={onChange} disabled={false} />);

    expect(screen.getByRole("group", { name: "Graph view" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Global graph" })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "Macro graph" }));
    expect(onChange).toHaveBeenCalledWith("macro");
  });
});
