"use client";

import Link from "next/link";
import { useActionState, useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/status-pill";
import { mockInkdeskDataSource } from "@/lib/mock-data-source";
import type { FormState, KnowledgeNoteDetail, NoteStatus } from "@/lib/types";

type FolderOption = {
  id: string;
  title: string;
};

type EditorViewProps = {
  initialMessage?: string;
  initialSaveState?: FormState;
  noteId: string;
  note?: KnowledgeNoteDetail;
  status: NoteStatus;
  folderOptions?: FolderOption[];
  saveAction?: (
    state: EditorSaveActionState,
    formData: FormData
  ) => Promise<EditorSaveActionState> | EditorSaveActionState;
};

export type EditorSaveActionState = {
  note?: KnowledgeNoteDetail;
  saveState: FormState;
  message?: string;
};

type ViewMode = "edit" | "preview" | "read";

function statusMeta(status: NoteStatus) {
  switch (status) {
    case "blank":
      return {
        label: "新建知识资产",
        tone: "neutral" as const,
        hint: "当前草稿还没有写入主系统"
      };
    case "loading":
      return {
        label: "正在载入上下文",
        tone: "soft" as const,
        hint: "请稍候"
      };
    case "saving":
      return {
        label: "同步主系统中",
        tone: "soft" as const,
        hint: "内容已进入同步队列"
      };
    case "error":
      return {
        label: "主系统未同步",
        tone: "warm" as const,
        hint: "当前内容仍保留在页面中"
      };
    case "published":
      return {
        label: "已发布到公开输出",
        tone: "soft" as const,
        hint: "公开输出已更新"
      };
    case "draft":
    default:
      return {
        label: "仅主系统可见",
        tone: "warm" as const,
        hint: "可以继续整理后再发布"
      };
  }
}

function countWords(value: string) {
  return value
    .replace(/[#>*`~-]/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function estimateReadingMinutes(value: string) {
  return Math.max(1, Math.ceil(Math.max(countWords(value), 1) / 220));
}

function splitParagraphs(value: string) {
  return value
    .split(/\r?\n\s*\r?\n/)
    .map((paragraph) => paragraph.replace(/\r?\n/g, " ").trim())
    .filter(Boolean);
}

async function defaultSaveAction(
  state: EditorSaveActionState,
  formData: FormData
): Promise<EditorSaveActionState> {
  const title = String(formData.get("title") ?? "").trim();
  const excerpt = String(formData.get("excerpt") ?? "").trim();
  const markdownContent = String(formData.get("markdownContent") ?? "");
  const parentId = String(formData.get("parentId") ?? "").trim();
  const note = state.note ?? mockInkdeskDataSource.getKnowledgeNoteById("note-002");

  return {
    note: {
      id: note?.id ?? "mock-note",
      parentId: parentId || note?.parentId,
      title: title || note?.title || "未命名知识资产",
      excerpt: excerpt || note?.excerpt || "",
      body: splitParagraphs(markdownContent),
      tags: note?.tags ?? [],
      folder: note?.folder ?? "知识资产",
      updatedAt: "刚刚保存",
      readingMinutes: estimateReadingMinutes(markdownContent),
      words: countWords(markdownContent),
      published: note?.published ?? false,
      visibility: note?.visibility ?? "private",
      visibilityLabel: note?.published ? "已发布" : "仅主系统",
      relatedPlanIds: note?.relatedPlanIds ?? [],
      relatedTagIds: note?.relatedTagIds ?? [],
      relatedSearchTerms: note?.relatedSearchTerms ?? [title || "知识资产"],
      knowledgeStateLabel: note?.published ? "已发布" : "仅主系统",
      slug: note?.slug
    },
    saveState: "success",
    message: "当前内容已写入本地 mock 预览状态。"
  };
}

export function EditorView({
  initialMessage,
  initialSaveState = "idle",
  noteId,
  note: providedNote,
  status,
  folderOptions = [],
  saveAction = defaultSaveAction
}: EditorViewProps) {
  const note = providedNote ?? mockInkdeskDataSource.getKnowledgeNoteById(noteId);
  const initialState: EditorSaveActionState = {
    message: initialMessage,
    note,
    saveState: initialSaveState
  };
  const [serverState, formAction, isPending] = useActionState(saveAction, initialState);
  const resolvedNote = serverState.note ?? note;
  const formKey = serverState.note?.updatedAt ?? note?.updatedAt ?? `${noteId}-${status}`;

  return (
    <EditorViewBody
      key={formKey}
      folderOptions={folderOptions}
      formAction={formAction}
      isPending={isPending}
      message={serverState.message}
      note={resolvedNote}
      saveState={serverState.saveState}
      status={status}
    />
  );
}

function EditorViewBody({
  note,
  status,
  folderOptions,
  saveState: initialSaveState,
  message,
  formAction,
  isPending
}: {
  note?: KnowledgeNoteDetail;
  status: NoteStatus;
  folderOptions: FolderOption[];
  saveState: FormState;
  message?: string;
  formAction: (formData: FormData) => void;
  isPending: boolean;
}) {
  const meta = statusMeta(status);
  const isBlank = status === "blank";
  const isLoading = status === "loading";
  const isError = status === "error";
  const isPublished = status === "published" || note?.published;
  const relatedPlans = useMemo(
    () => (note?.relatedPlanIds ?? []).map((planId) => mockInkdeskDataSource.getPlanById(planId)).filter(Boolean),
    [note?.relatedPlanIds]
  );
  const [mode, setMode] = useState<ViewMode>(isPublished ? "preview" : "edit");
  const [title, setTitle] = useState(note?.title ?? "");
  const [excerpt, setExcerpt] = useState(note?.excerpt ?? "");
  const [content, setContent] = useState(() => (note?.body ?? []).join("\n\n"));
  const [parentId, setParentId] = useState(note?.parentId ?? folderOptions[0]?.id ?? "");
  const [saveState, setSaveState] = useState<FormState>(initialSaveState);
  const renderedParagraphs = splitParagraphs(content);
  const relatedSearchTerm = (note?.relatedSearchTerms[0] ?? title) || "知识资产";
  const folderTitle = folderOptions.find((folder) => folder.id === parentId)?.title ?? note?.folder ?? "知识资产";
  const saveLabel = isPending ? "保存中..." : saveState === "success" ? "已保存到主系统" : "保存到主系统";
  const syncLabel = isPublished ? "已发布到公开输出" : "尚未发布";

  function markDirty() {
    if (saveState !== "idle") {
      setSaveState("idle");
    }
  }

  if (!note && !isBlank) {
    return (
      <main className="mx-auto max-w-reading px-6 py-16">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识资产不存在</div>
        <h1 className="mt-4 font-headline text-5xl font-extrabold tracking-tight text-ink-text">当前知识资产没有被找到</h1>
      </main>
    );
  }

  return (
    <form action={formAction}>
      <div className="grid min-h-[calc(100vh-81px)] xl:grid-cols-[minmax(0,1fr)_340px]">
        <article className="bg-ink-surface px-6 py-10 md:px-10 lg:px-16">
          {isError ? (
            <div className="mb-8 rounded-[20px] border border-[#f2b8b5] bg-ink-errorSoft px-5 py-4 text-ink-errorText">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined">cloud_off</span>
                <p className="font-headline text-sm font-semibold">主系统同步失败，请检查网络后重试。当前内容仍保留在页面里。</p>
              </div>
            </div>
          ) : null}

          {saveState === "success" ? (
            <div className="mb-6 rounded-[20px] bg-ink-primarySoft px-5 py-4 text-sm text-ink-primary">
              {message ?? "知识资产已写入主系统。"}
            </div>
          ) : null}

          {saveState === "error" ? (
            <div className="mb-6 rounded-[20px] bg-ink-errorSoft px-5 py-4 text-sm text-ink-errorText">
              {message ?? "保存失败，请稍后重试。"}
            </div>
          ) : null}

          <div className="rounded-[28px] bg-white px-5 py-5 shadow-paper">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识资产状态</div>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <StatusPill tone={meta.tone}>{meta.label}</StatusPill>
                  <StatusPill>{isBlank ? "仅主系统" : note?.visibilityLabel ?? "仅主系统"}</StatusPill>
                  <StatusPill tone={isPublished ? "soft" : "neutral"}>{syncLabel}</StatusPill>
                  <StatusPill tone="neutral">自动保存 需确认</StatusPill>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button className="rounded-sm bg-ink-primary px-4 py-3 font-headline text-sm font-semibold text-white" type="submit">
                  {saveLabel}
                </button>
                <Link href="/app/publish" className="rounded-sm bg-white px-4 py-3 text-center font-headline text-sm font-semibold text-ink-text">
                  {isPublished ? "更新公开输出" : "去发布模块"}
                </Link>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {[
                { key: "edit" as const, label: "编辑" },
                { key: "preview" as const, label: "预览" },
                { key: "read" as const, label: "只读" }
              ].map((item) => (
                <button
                  key={item.key}
                  className={`rounded-full px-4 py-2 text-sm ${mode === item.key ? "bg-ink-primary text-white" : "bg-ink-low text-ink-muted"}`}
                  onClick={() => setMode(item.key)}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="mt-4 grid gap-3 text-sm text-ink-muted md:grid-cols-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">可见范围</div>
                <div className="mt-2 text-ink-text">{isBlank ? "仅主系统" : note?.visibilityLabel}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">最近更新时间</div>
                <div className="mt-2 text-ink-text">{isBlank ? "尚未保存" : note?.updatedAt}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">当前说明</div>
                <div className="mt-2 text-ink-text">{meta.hint}</div>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="mt-10 space-y-5">
              <div className="h-5 w-48 animate-pulse rounded-sm bg-ink-low" />
              <div className="h-16 w-full animate-pulse rounded-sm bg-ink-low" />
              <div className="h-16 w-3/4 animate-pulse rounded-sm bg-ink-low" />
              <div className="mt-10 h-4 w-full animate-pulse rounded-sm bg-ink-low" />
              <div className="h-4 w-full animate-pulse rounded-sm bg-ink-low" />
              <div className="h-4 w-5/6 animate-pulse rounded-sm bg-ink-low" />
              <div className="h-48 w-full animate-pulse rounded-sm bg-ink-low" />
            </div>
          ) : (
            <>
              <div className="mt-10 max-w-reading">
                <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{folderTitle}</div>

                {mode === "edit" ? (
                  <input
                    className="mt-5 w-full bg-transparent font-headline text-5xl font-extrabold leading-[1.04] tracking-tight text-ink-text outline-none md:text-6xl"
                    name="title"
                    onChange={(event) => {
                      setTitle(event.target.value);
                      markDirty();
                    }}
                    placeholder="输入标题..."
                    value={title}
                  />
                ) : (
                  <h2 className="mt-5 font-headline text-5xl font-extrabold leading-[1.04] tracking-tight text-ink-text md:text-6xl">
                    {title || "未命名知识资产"}
                  </h2>
                )}

                <div className="mt-8 h-[2px] w-20 bg-ink-primary/20" />
              </div>

              <div className="mt-8 flex items-center gap-3 text-sm text-ink-muted">
                <span>当前视图</span>
                <StatusPill tone={mode === "edit" ? "soft" : "neutral"}>编辑</StatusPill>
                <StatusPill tone={mode === "preview" ? "soft" : "neutral"}>预览</StatusPill>
                <StatusPill tone={mode === "read" ? "soft" : "neutral"}>只读</StatusPill>
              </div>

              {mode === "edit" ? (
                <div className="mt-8 max-w-reading space-y-5">
                  <label className="block">
                    <span className="mb-2 block text-[11px] uppercase tracking-[0.2em] text-ink-muted">摘要</span>
                    <textarea
                      className="min-h-28 w-full rounded-[24px] border border-black/5 bg-white px-6 py-5 text-base leading-7 text-[#313738] shadow-paper focus:ring-2 focus:ring-ink-primary/20"
                      name="excerpt"
                      onChange={(event) => {
                        setExcerpt(event.target.value);
                        markDirty();
                      }}
                      placeholder="先写一句最能代表这篇知识资产的摘要。"
                      value={excerpt}
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-[11px] uppercase tracking-[0.2em] text-ink-muted">正文（Markdown）</span>
                    <textarea
                      className="min-h-[420px] w-full rounded-[28px] border border-black/5 bg-white px-6 py-6 font-body text-[1.1rem] leading-[1.85] text-[#313738] shadow-paper focus:ring-2 focus:ring-ink-primary/20"
                      name="markdownContent"
                      onChange={(event) => {
                        setContent(event.target.value);
                        markDirty();
                      }}
                      placeholder="开始记录你的思考，先写下一句你最确定的话。"
                      value={content}
                    />
                  </label>
                </div>
              ) : (
                <div className="mt-12 max-w-reading space-y-8 font-body text-[1.35rem] leading-[1.85] text-[#313738]">
                  {excerpt ? <p className="rounded-[24px] bg-white px-6 py-5 text-base leading-8 text-ink-muted shadow-paper">{excerpt}</p> : null}
                  {renderedParagraphs.length === 0 ? (
                    <p className="italic text-[#a2acab]">开始记录你的思考，先写下一句你最确定的话。</p>
                  ) : (
                    renderedParagraphs.map((paragraph, index) =>
                      index === 1 ? (
                        <blockquote key={`${paragraph}-${index}`} className="border-l-4 border-ink-primary bg-ink-low px-6 py-5 text-[1.55rem] italic text-ink-text">
                          {paragraph}
                        </blockquote>
                      ) : (
                        <p key={`${paragraph}-${index}`}>{paragraph}</p>
                      )
                    )
                  )}
                </div>
              )}
            </>
          )}
        </article>

        <aside className="border-t border-black/5 bg-ink-low px-6 py-8 xl:border-t-0">
          <div className="rounded-sm bg-white px-5 py-5 shadow-paper">
            <div className="font-headline text-xs uppercase tracking-[0.18em] text-ink-muted">知识资产侧栏</div>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">字数</dt>
                <dd>{countWords(content)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">阅读时长</dt>
                <dd>{`${estimateReadingMinutes(content)} 分钟`}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">标签</dt>
                <dd>{note?.tags.join(" / ") || "-"}</dd>
              </div>
              <div className="space-y-2">
                <dt className="text-ink-muted">所属知识分区</dt>
                <dd>
                  <select
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-sm text-ink-text"
                    name="parentId"
                    onChange={(event) => {
                      setParentId(event.target.value);
                      markDirty();
                    }}
                    value={parentId}
                  >
                    {folderOptions.map((folder) => (
                      <option key={folder.id} value={folder.id}>
                        {folder.title}
                      </option>
                    ))}
                  </select>
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">关联计划</dt>
                <dd>{relatedPlans.length > 0 ? `${relatedPlans.length} 项` : "暂无"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-ink-muted">推荐下一步动作</dt>
                <dd>{isPublished ? "更新公开输出" : "继续整理后发布"}</dd>
              </div>
            </dl>
          </div>

          <div className="mt-5 rounded-sm bg-white px-5 py-5 shadow-paper">
            <div className="font-headline text-xs uppercase tracking-[0.18em] text-ink-muted">当前工作流</div>
            <div className="mt-4 space-y-3 text-sm text-ink-muted">
              <div>知识状态：{isBlank ? "新建中" : note?.knowledgeStateLabel}</div>
              <div>是否已发布到公开输出：{syncLabel}</div>
              <div>召回关键词：{note?.relatedSearchTerms.join(" / ") || title || "-"}</div>
            </div>
            <div className="mt-5 text-sm text-ink-muted">
              {relatedPlans.length > 0
                ? `当前被 ${relatedPlans.map((plan) => plan?.title).filter(Boolean).join(" / ")} 调用。`
                : "当前还没有被计划直接引用，但仍可被检索和 Agent 召回。"}
            </div>
          </div>

          <div className="mt-5 flex flex-col gap-3">
            <Link href="/app/library" className="rounded-sm bg-white px-4 py-3 text-center font-headline text-sm font-semibold text-ink-text">
              返回知识库
            </Link>
            <Link href={`/app/search?q=${encodeURIComponent(relatedSearchTerm)}`} className="rounded-sm bg-white px-4 py-3 text-center font-headline text-sm font-semibold text-ink-text">
              以当前内容继续检索
            </Link>
            <Link href="/app/plans" className="rounded-sm bg-white px-4 py-3 text-center font-headline text-sm font-semibold text-ink-text">
              查看关联计划
            </Link>
            <Link href="/app/publish" className="rounded-sm bg-white px-4 py-3 text-center font-headline text-sm font-semibold text-ink-text">
              打开发布模块
            </Link>
          </div>
        </aside>
      </div>
    </form>
  );
}
