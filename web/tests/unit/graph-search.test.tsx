import React from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Node } from "@xyflow/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GraphSearch } from "@/components/workbench/graph-search";
import { findGraphNodes } from "@/lib/graph-search";
import type { GraphNodeData } from "@/lib/graph-layout";

const setCenter = vi.hoisted(() => vi.fn());

vi.mock("@xyflow/react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@xyflow/react")>();
  return {
    ...actual,
    useReactFlow: () => ({ setCenter })
  };
});

const nodes: Node<GraphNodeData>[] = [
  {
    id: "order-service",
    type: "entity",
    position: { x: 100, y: 60 },
    width: 280,
    height: 80,
    data: {
      label: "OrderBookingService",
      module: "link-service",
      kind: "entity",
      path: "services/OrderBookingService.java",
      status: "stable",
      summary: ""
    }
  },
  {
    id: "order-doc",
    type: "action",
    position: { x: 400, y: 160 },
    data: {
      label: "Order booking design.md",
      kind: "action",
      path: "wiki/order-booking-design.md",
      status: "draft",
      summary: ""
    }
  },
  {
    id: "batch-task",
    type: "entity",
    position: { x: 700, y: 260 },
    data: {
      label: "BatchPersistenceTask",
      kind: "entity",
      path: "tasks/BatchPersistenceTask.java",
      status: "stable",
      summary: ""
    }
  }
];

describe("graph search", () => {
  beforeEach(() => {
    setCenter.mockReset();
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
  });

  it("ranks exact and prefix label matches before path substrings", () => {
    expect(findGraphNodes(nodes, "order").map((node) => node.id)).toEqual(["order-doc", "order-service"]);
    expect(findGraphNodes(nodes, "OrderBookingService").map((node) => node.id)).toEqual(["order-service"]);
  });

  it("opens with Ctrl+K and centers the selected result with the keyboard", async () => {
    const user = userEvent.setup();
    const onNodeFocus = vi.fn();
    render(<GraphSearch nodes={nodes} onNodeFocus={onNodeFocus} />);

    const input = screen.getByRole("combobox", { name: "Search graph nodes" });
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(input).toHaveFocus();

    await user.type(input, "OrderBookingService");
    expect(screen.getByRole("option", { name: /OrderBookingService/ })).toBeInTheDocument();
    await user.keyboard("{Enter}");

    expect(setCenter).toHaveBeenCalledWith(240, 100, { zoom: 1.2, duration: 240 });
    expect(onNodeFocus).toHaveBeenCalledWith("order-service");
    expect(input).toHaveValue("");
  });

  it("supports arrow navigation, empty feedback, and Escape", async () => {
    const user = userEvent.setup();
    render(<GraphSearch nodes={nodes} onNodeFocus={vi.fn()} />);
    const input = screen.getByRole("combobox", { name: "Search graph nodes" });

    await user.type(input, "order");
    await user.keyboard("{ArrowDown}{Enter}");
    expect(setCenter).toHaveBeenCalledWith(540, 184, { zoom: 1.2, duration: 240 });

    await user.type(input, "missing-node");
    expect(screen.getByText("NO MATCHING NODES")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(input).toHaveValue("");
  });
});
