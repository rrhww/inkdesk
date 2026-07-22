"use client";

import { useEffect, useId, useRef, useState } from "react";

type MermaidState = "loading" | "ready" | "error";

let mermaidLoader: Promise<(typeof import("mermaid"))["default"]> | null = null;

function loadMermaid() {
  mermaidLoader ??= import("mermaid").then(({ default: mermaid }) => {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      flowchart: { htmlLabels: false },
      themeVariables: {
        primaryColor: "#F8FAFC",
        primaryTextColor: "#1E293B",
        primaryBorderColor: "#CBD5E1",
        lineColor: "#64748B",
        secondaryColor: "#D1FAE5",
        tertiaryColor: "#F1F5F9"
      }
    });
    return mermaid;
  });
  return mermaidLoader;
}

export function MermaidDiagram({ chart }: { chart: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reactId = useId();
  const diagramId = `inkdesk-mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const [state, setState] = useState<MermaidState>("loading");

  useEffect(() => {
    let active = true;
    containerRef.current?.replaceChildren();

    void loadMermaid()
      .then((mermaid) => mermaid.render(diagramId, chart))
      .then(({ svg }) => {
        if (!active || !containerRef.current) {
          return;
        }
        const parsed = new DOMParser().parseFromString(svg, "image/svg+xml");
        if (parsed.querySelector("parsererror") || parsed.documentElement.tagName.toLowerCase() !== "svg") {
          throw new Error("Mermaid returned invalid SVG");
        }
        const diagram = document.importNode(parsed.documentElement, true);
        diagram.setAttribute("aria-hidden", "true");
        diagram.setAttribute("focusable", "false");
        diagram.classList.add("h-auto", "max-w-full");
        containerRef.current.replaceChildren(diagram);
        setState("ready");
      })
      .catch(() => {
        if (active) {
          setState("error");
        }
      });

    return () => {
      active = false;
    };
  }, [chart, diagramId]);

  return (
    <figure
      role="img"
      aria-label="Mermaid architecture diagram"
      className="not-prose my-6 overflow-x-auto border border-slate-300 bg-slate-50 p-4"
    >
      <div ref={containerRef} className={state === "ready" ? "flex min-h-24 justify-center" : "hidden"} />
      {state === "loading" ? (
        <p role="status" className="m-0 py-8 text-center font-mono text-xs tracking-widest text-slate-500">
          RENDERING ARCHITECTURE
        </p>
      ) : null}
      {state === "error" ? (
        <div className="border-l-2 border-rose-500 pl-4">
          <p role="alert" className="m-0 font-mono text-xs font-semibold text-slate-800">
            Mermaid diagram could not be rendered
          </p>
          <pre className="mt-3 overflow-x-auto border border-slate-300 bg-white p-3 text-xs text-slate-700">
            <code>{chart}</code>
          </pre>
        </div>
      ) : null}
    </figure>
  );
}
