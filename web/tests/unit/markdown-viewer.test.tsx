import React from "react";

import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MarkdownViewer } from "@/components/workbench/markdown-viewer";

const mermaidMocks = vi.hoisted(() => ({
  initialize: vi.fn(),
  render: vi.fn()
}));

vi.mock("mermaid", () => ({ default: mermaidMocks }));

describe("MarkdownViewer", () => {
  beforeEach(() => {
    mermaidMocks.initialize.mockReset();
    mermaidMocks.render.mockReset();
  });

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

  it("renders Mermaid fences as secure diagrams while leaving ordinary code highlighted", async () => {
    mermaidMocks.render.mockResolvedValue({
      svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><title>Flow</title></svg>'
    });

    const { container } = render(
      <MarkdownViewer
        content={`
\`\`\`mermaid
graph TD
  A --> B
\`\`\`

\`\`\`ts
const ready = true;
\`\`\`
`}
        isLoading={false}
      />
    );

    expect(await screen.findByRole("img", { name: "Mermaid architecture diagram" })).toBeInTheDocument();
    await waitFor(() => expect(container.querySelector("svg")).toBeInTheDocument());
    expect(container.querySelector("pre code.hljs.language-ts")).toBeInTheDocument();
    expect(mermaidMocks.initialize).toHaveBeenCalledWith(expect.objectContaining({ securityLevel: "strict" }));
    expect(mermaidMocks.render).toHaveBeenCalledWith(expect.any(String), "graph TD\n  A --> B");
  });

  it("shows a stable fallback when Mermaid syntax cannot be rendered", async () => {
    mermaidMocks.render.mockRejectedValue(new Error("bad diagram"));

    render(
      <MarkdownViewer
        content={`\`\`\`mermaid
graph TD broken
\`\`\``}
        isLoading={false}
      />
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Mermaid diagram could not be rendered");
    expect(screen.getByText("graph TD broken")).toBeInTheDocument();
  });

  it("renders stable loading and empty states", () => {
    const { rerender } = render(<MarkdownViewer content="" isLoading />);
    expect(screen.getByRole("status", { name: "正在读取 Markdown" })).toBeInTheDocument();

    rerender(<MarkdownViewer content="" isLoading={false} />);
    expect(screen.getByText("EOF / EMPTY DOCUMENT")).toBeInTheDocument();
  });
});
