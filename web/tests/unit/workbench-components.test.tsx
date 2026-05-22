import React from "react";

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/app-header";
import { AppSidebarContent } from "@/components/app-sidebar";
import { AskAnswerCard } from "@/components/workbench/ask-answer-card";
import { OwnerLoginForm } from "@/components/workbench/owner-login-form";
import { ReviewCard } from "@/components/workbench/review-card";
import { getAppRouteChrome } from "@/lib/app-shell";
import { researchDashboardFixture } from "@/lib/mock/research-fixtures";
import { researchReviewItemsFixture } from "@/lib/mock/research-fixtures";

describe("workbench components", () => {
  afterEach(() => {
    vi.restoreAllMocks();
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

  it("renders Chinese top tabs and ask-first rail", () => {
    const chrome = getAppRouteChrome("/app/raw", researchDashboardFixture);

    render(
      <>
        <AppHeader
          title={chrome.title}
          subtitle={chrome.subtitle}
          contextItems={chrome.contextItems}
        />
        <AppSidebarContent pathname="/app" snapshot={researchDashboardFixture} />
      </>
    );

    expect(screen.getByRole("heading", { name: "资料" })).toBeInTheDocument();
    expect(screen.getByText(/raw 材料进入系统后的第一站/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "问答" })).toHaveAttribute("href", "/app");
    expect(screen.getByRole("link", { name: "资料" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "审阅" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "知识库" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "健康" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /知识健康/ })).toHaveAttribute("href", "/app");
    expect(screen.getByText("raw 里有 3 条材料等待编译")).toBeInTheDocument();
    expect(screen.getByText("最近对话")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建对话" })).toBeInTheDocument();
  });

  it("renders claim governance metadata inside review cards", () => {
    render(
      <ReviewCard
        actions={null}
        review={researchReviewItemsFixture[0]}
      />
    );

    expect(screen.getByText(/重审提案/)).toBeInTheDocument();
    expect(screen.getByText(/unsupported/i)).toBeInTheDocument();
    expect(screen.getByText(/证据 0 条/)).toBeInTheDocument();
    expect(screen.getByText(/使用 4 次/)).toBeInTheDocument();
    expect(screen.getByText("需要重审")).toBeInTheDocument();
    expect(screen.getByText(/最近使用 2026-05-04/)).toBeInTheDocument();
    expect(screen.getByText(/最近验证 2026-04-13/)).toBeInTheDocument();
    expect(screen.getByText("存在冲突")).toBeInTheDocument();
    expect(screen.getByText(/当前和同主题里的另一条判断互相打架/)).toBeInTheDocument();
  });

  it("renders citations without duplicate React key warnings when multiple citations share a source", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <AskAnswerCard
        answer={{
          id: "ask-turn-1",
          question: "当前最重要的理解是什么？",
          answer: "当前最重要的理解是先把 raw 编译进 wiki。",
          confidence: 0.86,
          followUpQuestions: [],
          knowledgeGaps: [],
          usedWikiIds: ["topic-1"],
          usedSourceIds: ["source-1"],
          usedWebSources: [],
          contextAskTurnIds: [],
          canWriteback: true,
          citations: [
            {
              sourceId: "source-1",
              chunkId: "chunk-1",
              title: "资料一",
              locator: "第 1 段"
            },
            {
              sourceId: "source-1",
              chunkId: "chunk-2",
              title: "资料一",
              locator: "第 2 段"
            }
          ],
          createdAt: "2026-05-19T00:00:00Z"
        }}
        mode="vault"
        renderFollowUpHref={() => "/app"}
        writebackAction={<button type="button">沉淀到 wiki</button>}
      />
    );

    expect(screen.getAllByText("资料一")).toHaveLength(2);
    expect(
      errorSpy.mock.calls.some((call) => call.some((value) => String(value).includes("same key")))
    ).toBe(false);
  });
});
