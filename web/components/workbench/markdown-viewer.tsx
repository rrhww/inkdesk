import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import "highlight.js/styles/github-dark-dimmed.css";

type MarkdownViewerProps = {
  content: string;
  isLoading: boolean;
};

export function stripFrontmatter(content: string) {
  const normalized = content.replace(/\r\n/g, "\n");
  if (!normalized.startsWith("---\n")) {
    return content;
  }

  const end = normalized.indexOf("\n---\n", 4);
  return end < 0 ? content : normalized.slice(end + 5).trimStart();
}

export function MarkdownViewer({ content, isLoading }: MarkdownViewerProps) {
  if (isLoading) {
    return (
      <div role="status" aria-label="正在读取 Markdown" className="space-y-4 pt-2">
        <span className="sr-only">正在读取 Markdown</span>
        <div aria-hidden="true" className="space-y-4 motion-safe:animate-pulse motion-reduce:animate-none">
          <div className="h-7 w-2/5 bg-slate-200" />
          <div className="h-3 w-4/5 bg-slate-100" />
          <div className="h-3 w-full bg-slate-100" />
          <div className="h-3 w-3/4 bg-slate-100" />
          <div className="mt-6 h-28 w-full bg-slate-100" />
        </div>
      </div>
    );
  }

  const markdown = stripFrontmatter(content).trim();
  if (!markdown) {
    return <p className="mt-4 font-mono text-xs text-slate-500">EOF / EMPTY DOCUMENT</p>;
  }

  return (
    <article className="markdown-viewer prose prose-sm prose-slate max-w-none prose-headings:font-label prose-headings:tracking-normal prose-headings:text-slate-900 prose-a:text-emerald-700 prose-a:underline prose-a:underline-offset-4 hover:prose-a:text-emerald-600 prose-pre:rounded-none prose-pre:border prose-pre:border-slate-800 prose-pre:bg-slate-900 prose-pre:p-0 prose-pre:text-slate-200 prose-table:font-mono prose-table:text-xs prose-th:border prose-th:border-slate-300 prose-th:bg-slate-50 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-slate-200 prose-td:px-3 prose-td:py-2 [&_:not(pre)>code]:rounded-none [&_:not(pre)>code]:bg-emerald-50 [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:py-0.5 [&_:not(pre)>code]:text-emerald-800 [&_:not(pre)>code]:before:content-none [&_:not(pre)>code]:after:content-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
