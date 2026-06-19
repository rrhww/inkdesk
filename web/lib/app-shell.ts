import type { ResearchAskHistoryEntry, ResearchDashboard } from "@/lib/types";

export const PRIMARY_SECTIONS = [
  { href: "/app", label: "任务", matchers: ["/app"], exact: true },
  { href: "/app/ask", label: "问答", matchers: ["/app/ask"] },
  { href: "/app/raw", label: "资料", matchers: ["/app/raw"] },
  { href: "/app/ingest", label: "审阅", matchers: ["/app/ingest"] },
  { href: "/app/wiki", label: "知识库", matchers: ["/app/wiki"] }
] as const;

export type AppHeaderContextItem = {
  label: string;
  value: string;
};

export type AppRouteChrome = {
  title: string;
  subtitle: string;
  contextItems: AppHeaderContextItem[];
};

export function pathnameMatchesSection(pathname: string, section: (typeof PRIMARY_SECTIONS)[number]) {
  return section.matchers.some((matcher) => {
    if ("exact" in section && section.exact) {
      return pathname === matcher;
    }

    return pathname === matcher || pathname.startsWith(`${matcher}/`);
  });
}

export function getPrimarySectionForPathname(pathname: string) {
  return PRIMARY_SECTIONS.find((section) => pathnameMatchesSection(pathname, section));
}

export function getAppRouteChrome(pathname: string, snapshot: ResearchDashboard): AppRouteChrome {
  if (pathname === "/app/raw" || pathname.startsWith("/app/raw/")) {
    return {
      title: "资料",
      subtitle: "raw 材料进入系统后的第一站：保存原文、来源位置和 vault 路径，等待 AI 编译成 ingest 提案。",
      contextItems: [
        { label: "等待编译", value: `${snapshot.health.rawBacklogCount} 条` },
        { label: "全部资料", value: `${snapshot.summary.totalSources} 条` },
        { label: "最新来源", value: snapshot.recentSources[0]?.kind ?? "待导入" }
      ]
    };
  }

  if (pathname === "/app/ingest" || pathname.startsWith("/app/ingest/")) {
    return {
      title: "审阅",
      subtitle: "ingest 是知识写入前的人工闸门：AI 只能提出提案，你决定哪些理解可以进入 wiki。",
      contextItems: [
        { label: "待审阅", value: `${snapshot.health.reviewBacklogCount} 条` },
        { label: "开放问题", value: `${snapshot.health.openQuestionCount} 个` },
        { label: "可写回", value: `${snapshot.health.writebackCandidateCount} 条` }
      ]
    };
  }

  if (pathname === "/app/wiki" || pathname.startsWith("/app/wiki/")) {
    const highRiskClaimCount = snapshot.health.unsupportedClaimCount + snapshot.health.staleClaimCount;
    return {
      title: "知识库",
      subtitle: "wiki 是长期知识层：沉淀 current understanding、claims、sources，并持续暴露 open questions。",
      contextItems: [
        { label: "知识页", value: `${snapshot.summary.activeTopics} 个` },
        { label: "开放问题", value: `${snapshot.health.openQuestionCount} 个` },
        { label: "高风险 claim", value: `${highRiskClaimCount} 条` },
        { label: "冲突 claim", value: `${snapshot.health.conflictingClaimCount} 条` },
        { label: "焦点主题", value: snapshot.focusTopic?.title ?? "暂无" }
      ]
    };
  }

  if (pathname === "/app" || pathname.startsWith("/app/ask")) {
    if (pathname === "/app") {
      return {
        title: "研发任务",
        subtitle: "Dev Run Console：从 PRD / bug / 改造任务出发，沿着 context → solution → review → coding → testing → deposit 推进，每个阶段的输出都沉淀到知识库。",
        contextItems: [
          { label: "当前入口", value: "Dev Run Console" },
          { label: "知识缺口", value: `${snapshot.health.knowledgeGapCount} 个` },
          { label: "待审阅", value: `${snapshot.health.reviewBacklogCount} 条` }
        ]
      };
    }
    return {
      title: "问答",
      subtitle: "Ask 现在是主入口：先暴露知识缺口，再指向下一步安全动作，回答仍然保持 vault-first 和显式联网补料纪律。",
      contextItems: [
        { label: "当前模式", value: "Ask-first" },
        { label: "知识缺口", value: `${snapshot.health.knowledgeGapCount} 个` },
        { label: "可写回", value: `${snapshot.health.writebackCandidateCount} 条` }
      ]
    };
  }

  return {
    title: "问答",
    subtitle: "Ask 现在是主入口：先暴露知识缺口，再指向下一步安全动作，回答仍然保持 vault-first 和显式联网补料纪律。",
    contextItems: [
      { label: "当前模式", value: "Ask-first" },
      { label: "知识缺口", value: `${snapshot.health.knowledgeGapCount} 个` },
      { label: "可写回", value: `${snapshot.health.writebackCandidateCount} 条` }
    ]
  };
}

export function buildStarterHistory(input: {
  suggestedQuestions: string[];
  focusTopicId?: string | null;
  focusTopicTitle?: string | null;
}): ResearchAskHistoryEntry[] {
  return input.suggestedQuestions.slice(0, 3).map((question, index) => ({
    id: `starter-${index + 1}`,
    title: question,
    href: buildStarterHref(question, input.focusTopicId),
    topicTitle: input.focusTopicTitle ?? "研究入口",
    preview: "从这里开始新的研究追问。",
    updatedAt: "2026-05-03T00:00:00Z"
  }));
}

function buildStarterHref(question: string, topicId?: string | null) {
  const href = `/app?q=${encodeURIComponent(question)}`;
  return topicId ? `${href}&topicId=${encodeURIComponent(topicId)}` : href;
}
