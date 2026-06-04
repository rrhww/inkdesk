import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { PageShell } from "@/components/workbench/page-shell";
import { SourceCard } from "@/components/workbench/source-card";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";
import { requireRequestOwnerSession } from "@/lib/request-owner-session";
import { getRawSources, importPdfSource, importTextSource, importWebSource } from "@/lib/research";

async function importWebAction(formData: FormData) {
  "use server";

  const cookieStore = await cookies();
  await importWebSource(
    {
      url: String(formData.get("url") ?? ""),
      title: String(formData.get("title") ?? "").trim() || undefined
    },
    cookieStore.get(OWNER_SESSION_COOKIE)?.value
  );
  revalidatePath("/app");
  revalidatePath("/app/raw");
  revalidatePath("/app/ingest");
}

async function importTextAction(formData: FormData) {
  "use server";

  const cookieStore = await cookies();
  await importTextSource(
    {
      title: String(formData.get("title") ?? ""),
      locator: String(formData.get("locator") ?? "").trim() || undefined,
      body: String(formData.get("body") ?? ""),
      excerpt: String(formData.get("excerpt") ?? "").trim() || undefined
    },
    cookieStore.get(OWNER_SESSION_COOKIE)?.value
  );
  revalidatePath("/app");
  revalidatePath("/app/raw");
  revalidatePath("/app/ingest");
}

async function importPdfAction(formData: FormData) {
  "use server";

  const file = formData.get("file");
  if (!(file instanceof File)) {
    return;
  }

  const cookieStore = await cookies();
  await importPdfSource(
    file,
    String(formData.get("title") ?? "").trim() || undefined,
    cookieStore.get(OWNER_SESSION_COOKIE)?.value,
    String(formData.get("locator") ?? "").trim() || undefined
  );
  revalidatePath("/app");
  revalidatePath("/app/raw");
  revalidatePath("/app/ingest");
}

export default async function RawPage() {
  const ownerSession = await requireRequestOwnerSession();
  const sources = await getRawSources(ownerSession);
  const pending = sources.filter((source) => source.status === "RAW" || source.status === "INGEST_PENDING");

  return (
    <PageShell
      eyebrow="raw"
      title="原始材料 vault"
      description="raw/ 是所有网页、PDF 和迁移旧笔记的入口。这里保存原始材料与 provenance，ingest 只能基于这些 raw 文件提出 wiki 变更。"
    >
      <div className="mt-8 grid gap-6 xl:grid-cols-3">
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">导入网页</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">输入 URL，系统抓取正文与标题，再写入 raw。</p>
          <form action={importWebAction} className="mt-5 space-y-3">
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
        </PanelCard>
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">导入文本</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">粘贴个人笔记、访谈摘录或临时研究材料，直接进入 raw。</p>
          <form action={importTextAction} className="mt-5 space-y-3">
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
        </PanelCard>
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">导入 PDF</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">上传 PDF，系统抽取文本后落进 raw，并生成后续 ingest 提案。</p>
          <form action={importPdfAction} className="mt-5 space-y-3">
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
        </PanelCard>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">vault 规则</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">
            迁移旧笔记、抓取网页和导入 PDF 都会先生成 raw markdown。AI 只能提出 ingest 提案，不能直接写入 wiki。
          </p>
        </PanelCard>
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">等待 ingest</div>
          <div className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{pending.length}</div>
          <p className="mt-2 text-sm text-ink-muted">优先处理最新 raw，把有价值的内容送入 ingest 队列。</p>
        </PanelCard>
      </div>

      <div className="mt-8 space-y-4">
        {sources.length > 0 ? (
          sources.map((source) => <SourceCard key={source.id} source={source} />)
        ) : (
          <EmptyState
            eyebrow="raw empty"
            title="还没有原始材料"
            description="先导入网页、文本或 PDF。Inkdesk 会把它们保存在 raw，再交给 ingest 生成可审阅提案。"
            actionLabel="导入第一份材料"
            href="/app/raw"
          />
        )}
      </div>
    </PageShell>
  );
}
