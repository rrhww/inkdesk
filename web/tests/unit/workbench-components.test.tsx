import React from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { EditorView } from "@/components/editor-view";
import { AgentConsole } from "@/components/workbench/agent-console";
import { OwnerLoginForm } from "@/components/workbench/owner-login-form";
import { SettingsWorkspace } from "@/components/workbench/settings-workspace";
import { mockInkdeskDataSource } from "@/lib/mock-data-source";

describe("workbench components", () => {
  it("renders agent console quick actions and publish queue", () => {
    render(React.createElement(AgentConsole, { snapshot: mockInkdeskDataSource.getWorkbenchSnapshot() }));

    expect(screen.getByText("快速动作")).toBeInTheDocument();
    expect(screen.getAllByText("待发布内容").length).toBeGreaterThan(0);
  });

  it("renders owner login form fields with robust metadata", () => {
    render(
      React.createElement(OwnerLoginForm, {
        action: async () => {},
        hasError: false
      })
    );

    expect(screen.getByLabelText("邮箱")).toHaveAttribute("type", "email");
    expect(screen.getByLabelText("密码")).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByText(/主人身份/)).toBeInTheDocument();
  });

  it("allows settings toggles to be changed locally", async () => {
    const user = userEvent.setup();

    render(React.createElement(SettingsWorkspace, { initialSettings: mockInkdeskDataSource.getSettingsRecord() }));

    const compactToggle = screen.getByRole("button", { name: "紧凑模式" });
    await user.click(compactToggle);

    expect(compactToggle).toHaveAttribute("aria-pressed", "true");
  });

  it("shows manual-save mode for the knowledge asset editor", async () => {
    render(React.createElement(EditorView, { noteId: "note-002", status: "draft" }));

    expect(screen.getByText("自动保存 需确认")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存到主系统" })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("开始记录你的思考，先写下一句你最确定的话。"), {
      target: {
        value: "把首页 Agent 区域改成今天的聚焦视图。"
      }
    });

    expect(screen.getByText("自动保存 需确认")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存到主系统" })).toBeInTheDocument();
  });
});
