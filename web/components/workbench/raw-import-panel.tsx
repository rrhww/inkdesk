"use client";

import { useState } from "react";

type ImportTab = "web" | "text" | "pdf";

const TABS: { key: ImportTab; label: string; icon: string }[] = [
  { key: "web", label: "网页", icon: "language" },
  { key: "text", label: "文本", icon: "edit_note" },
  { key: "pdf", label: "PDF", icon: "picture_as_pdf" },
];

export function RawImportPanel({
  webAction,
  textAction,
  pdfAction,
}: {
  webAction: (formData: FormData) => Promise<void>;
  textAction: (formData: FormData) => Promise<void>;
  pdfAction: (formData: FormData) => Promise<void>;
}) {
  const [tab, setTab] = useState<ImportTab>("web");

  return (
    <div className="paper-card p-6">
      <div className="flex gap-1 mb-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-ink-primary text-white"
                : "text-ink-muted hover:text-ink-text hover:bg-ink-low"
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "web" && (
        <form action={webAction} className="space-y-3">
          <p className="text-sm leading-7 text-ink-muted">输入 URL，系统抓取正文与标题，再写入 raw。</p>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-web-url">
              网页 URL <span className="text-ink-errorText">*</span>
            </label>
            <input
              aria-describedby="raw-web-url-help"
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-web-url"
              name="url"
              placeholder="https://example.com/topic-memory"
              required
              type="url"
            />
            <p className="mt-2 text-xs leading-6 text-ink-muted" id="raw-web-url-help">
              系统会保存网页正文、原始 locator，并等待后续 ingest。
            </p>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-web-title">
              标题覆盖
            </label>
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-web-title"
              name="title"
              placeholder="可选标题覆盖"
              type="text"
            />
          </div>
          <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
            导入网页
          </button>
        </form>
      )}

      {tab === "text" && (
        <form action={textAction} className="space-y-3">
          <p className="text-sm leading-7 text-ink-muted">粘贴个人笔记、访谈摘录或临时研究材料，直接进入 raw。</p>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-text-title">
              材料标题 <span className="text-ink-errorText">*</span>
            </label>
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-text-title"
              name="title"
              placeholder="材料标题"
              required
              type="text"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-text-locator">
              locator
            </label>
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-text-locator"
              name="locator"
              placeholder="可选 locator，例如 local://memo"
              type="text"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-text-excerpt">
              摘录
            </label>
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-text-excerpt"
              name="excerpt"
              placeholder="可选摘录，不填则自动生成"
              type="text"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-text-body">
              正文 <span className="text-ink-errorText">*</span>
            </label>
            <textarea
              aria-describedby="raw-text-body-help"
              className="min-h-32 w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm leading-7 text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-text-body"
              name="body"
              placeholder="粘贴要进入 raw 的正文"
              required
            />
            <p className="mt-2 text-xs leading-6 text-ink-muted" id="raw-text-body-help">
              这会作为原始证据保存，不会直接进入 wiki。
            </p>
          </div>
          <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
            导入文本
          </button>
        </form>
      )}

      {tab === "pdf" && (
        <form action={pdfAction} className="space-y-3">
          <p className="text-sm leading-7 text-ink-muted">上传 PDF，系统抽取文本后落进 raw，并生成后续 ingest 提案。</p>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-pdf-title">
              标题覆盖
            </label>
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-pdf-title"
              name="title"
              placeholder="可选标题覆盖"
              type="text"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-pdf-locator">
              locator
            </label>
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none focus:ring-2 focus:ring-ink-primary/20"
              id="raw-pdf-locator"
              name="locator"
              placeholder="可选 locator"
              type="text"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-ink-text" htmlFor="raw-pdf-file">
              PDF 文件 <span className="text-ink-errorText">*</span>
            </label>
            <input
              accept="application/pdf"
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none file:mr-3 file:rounded-full file:border-0 file:bg-ink-low file:px-3 file:py-2 focus:ring-2 focus:ring-ink-primary/20"
              id="raw-pdf-file"
              name="file"
              required
              type="file"
            />
          </div>
          <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
            上传 PDF
          </button>
        </form>
      )}
    </div>
  );
}
