import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
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
  const ownerSession = await getRequestOwnerSession();
  const sources = await getRawSources(ownerSession);
  const pending = sources.filter((source) => source.status === "RAW" || source.status === "INGEST_PENDING");

  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <SectionHeading
        eyebrow="raw"
        title="原始材料 vault"
        description="raw/ 是所有网页、PDF 和迁移旧笔记的入口。这里保存原始材料与 provenance，ingest 只能基于这些 raw 文件提出 wiki 变更。"
      />

      <div className="mt-8 grid gap-6 xl:grid-cols-3">
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">导入网页</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">输入 URL，系统抓取正文与标题，再写入 raw。</p>
          <form action={importWebAction} className="mt-5 space-y-3">
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="url"
              placeholder="https://example.com/topic-memory"
              type="url"
            />
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="title"
              placeholder="可选标题覆盖"
              type="text"
            />
            <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
              导入网页
            </button>
          </form>
        </PanelCard>
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">导入文本</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">粘贴个人笔记、访谈摘录或临时研究材料，直接进入 raw。</p>
          <form action={importTextAction} className="mt-5 space-y-3">
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="title"
              placeholder="材料标题"
              type="text"
            />
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="locator"
              placeholder="可选 locator，例如 local://memo"
              type="text"
            />
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="excerpt"
              placeholder="可选摘录，不填则自动生成"
              type="text"
            />
            <textarea
              className="min-h-32 w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm leading-7 text-ink-text outline-none"
              name="body"
              placeholder="粘贴要进入 raw 的正文"
            />
            <button className="rounded-full bg-ink-primary px-5 py-3 text-sm font-semibold text-white" type="submit">
              导入文本
            </button>
          </form>
        </PanelCard>
        <PanelCard className="p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">导入 PDF</div>
          <p className="mt-4 text-sm leading-7 text-ink-muted">上传 PDF，系统抽取文本后落进 raw，并生成后续 ingest 提案。</p>
          <form action={importPdfAction} className="mt-5 space-y-3">
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="title"
              placeholder="可选标题覆盖"
              type="text"
            />
            <input
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none"
              name="locator"
              placeholder="可选 locator"
              type="text"
            />
            <input
              accept="application/pdf"
              className="w-full rounded-[18px] border border-black/10 bg-white px-4 py-3 text-sm text-ink-text outline-none file:mr-3 file:rounded-full file:border-0 file:bg-ink-low file:px-3 file:py-2"
              name="file"
              type="file"
            />
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
        {sources.map((source) => (
          <PanelCard key={source.id} className="p-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-ink-low px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-ink-muted">
                {source.kind}
              </span>
              <span className="rounded-full bg-ink-primarySoft px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-ink-primary">
                {source.status}
              </span>
            </div>
            <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{source.title}</h2>
            <p className="mt-3 text-sm leading-7 text-ink-muted">{source.excerpt}</p>
            {source.locator ? <p className="mt-3 text-sm text-ink-muted">{source.locator}</p> : null}
            {source.vaultPath ? <p className="mt-2 text-sm text-ink-primary">{source.vaultPath}</p> : null}
          </PanelCard>
        ))}
      </div>
    </main>
  );
}
