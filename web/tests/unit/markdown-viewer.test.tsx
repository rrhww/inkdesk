import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarkdownViewer } from "@/components/workbench/markdown-viewer";

describe("MarkdownViewer", () => {
  it("hides frontmatter and renders GFM tables with highlighted fenced code", () => {
    const { container } = render(
      <MarkdownViewer
        content={`---
type: concept
status: stable
---
# Graph Runtime

| Layer | State |
| --- | --- |
| Vault | Ready |

\`\`\`ts
const ready = true;
\`\`\`
`}
        isLoading={false}
      />
    );

    expect(screen.getByRole("heading", { name: "Graph Runtime" })).toBeInTheDocument();
    expect(screen.queryByText("type: concept")).not.toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(container.querySelector("code.hljs")).toHaveClass("language-ts");
  });

  it("does not execute raw HTML from Vault Markdown", () => {
    const { container } = render(
      <MarkdownViewer content={'<script data-testid="unsafe">window.pwned = true</script>'} isLoading={false} />
    );

    expect(container.querySelector("script")).toBeNull();
  });

  it("renders stable loading and empty states", () => {
    const { rerender } = render(<MarkdownViewer content="" isLoading />);
    expect(screen.getByRole("status", { name: "正在读取 Markdown" })).toBeInTheDocument();

    rerender(<MarkdownViewer content="" isLoading={false} />);
    expect(screen.getByText("EOF / EMPTY DOCUMENT")).toBeInTheDocument();
  });
});
