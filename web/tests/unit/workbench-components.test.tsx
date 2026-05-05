import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppHeader } from "@/components/app-header";
import { AppSidebarContent } from "@/components/app-sidebar";
import { OwnerLoginForm } from "@/components/workbench/owner-login-form";
import { ResearchDashboardView } from "@/components/workbench/research-dashboard";
import { researchDashboardFixture } from "@/lib/mock/research-fixtures";

describe("workbench components", () => {
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

  it("renders the vault dashboard around raw, ingest, wiki, and ask workflows", () => {
    render(React.createElement(ResearchDashboardView, { snapshot: researchDashboardFixture }));

    expect(screen.getByText("Today Vault Panel")).toBeInTheDocument();
    expect(screen.getAllByText("ingest 队列").length).toBeGreaterThan(0);
    expect(screen.getByText("最新 raw")).toBeInTheDocument();
    expect(screen.getByText("下一步路径")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "回到 raw" })).toHaveAttribute("href", "/app/raw");
  });

  it("renders Chinese top tabs and history-first rail", () => {
    render(
      <>
        <AppHeader
          title="问答"
          contextItems={[
            { label: "当前模式", value: "仅基于知识库" },
            { label: "待审阅", value: "3 条" }
          ]}
        />
        <AppSidebarContent pathname="/app" snapshot={researchDashboardFixture} />
      </>
    );

    expect(screen.getByRole("link", { name: "问答" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "资料" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "审阅" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "知识库" })).toBeInTheDocument();
    expect(screen.getByText("最近对话")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建对话" })).toBeInTheDocument();
  });
});
