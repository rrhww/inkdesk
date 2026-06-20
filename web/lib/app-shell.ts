import type { ResearchAskHistoryEntry, ResearchDashboard } from "@/lib/types";

export const PRIMARY_SECTIONS = [
  { href: "/app", label: "任务", matchers: ["/app"], exact: true },
  { href: "/app/ask", label: "问答", matchers: ["/app/ask"] },
  { href: "/app/raw", label: "资料", matchers: ["/app/raw"] },
  { href: "/app/ingest", label: "审阅", matchers: ["/app/ingest"] },
  { href: "/app/wiki", label: "知识库", matchers: ["/app/wiki"] },
  { href: "/app/health", label: "健康", matchers: ["/app/health"] },
  { href: "/app/compile", label: "编译", matchers: ["/app/compile"] },
] as const;

export type AppRouteChrome = {
  title: string;
  subtitle: string;
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

export function getAppRouteChrome(pathname: string, _snapshot: ResearchDashboard): AppRouteChrome {
  if (pathname === "/app/raw" || pathname.startsWith("/app/raw/")) {
    return {
      title: "资料",
      subtitle: "",
    };
  }

  if (pathname === "/app/ingest" || pathname.startsWith("/app/ingest/")) {
    return {
      title: "审阅",
      subtitle: "",
    };
  }

  if (pathname === "/app/health" || pathname.startsWith("/app/health/")) {
    return {
      title: "知识库健康",
      subtitle: "",
    };
  }

  if (pathname === "/app/compile" || pathname.startsWith("/app/compile/")) {
    return {
      title: "编译流水线",
      subtitle: "",
    };
  }

  if (pathname === "/app/wiki" || pathname.startsWith("/app/wiki/")) {
    return {
      title: "知识库",
      subtitle: "",
    };
  }

  if (pathname === "/app" || pathname.startsWith("/app/ask")) {
    if (pathname === "/app") {
      return {
        title: "研发任务",
        subtitle: "",
      };
    }
    return {
      title: "问答",
      subtitle: "",
    };
  }

  return {
    title: "问答",
    subtitle: "",
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
