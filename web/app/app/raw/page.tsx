import { revalidatePath } from "next/cache";

import { EmptyState } from "@/components/ui/empty-state";
import { PageShell } from "@/components/workbench/page-shell";
import { RawImportPanel } from "@/components/workbench/raw-import-panel";
import { SourceCard } from "@/components/workbench/source-card";
import { getRawSources, importPdfSource, importTextSource, importWebSource } from "@/lib/research";

async function importWebAction(formData: FormData) {
  "use server";

  await importWebSource(
    {
      url: String(formData.get("url") ?? ""),
      title: String(formData.get("title") ?? "").trim() || undefined,
    },
  );
  revalidatePath("/app");
  revalidatePath("/app/raw");
  revalidatePath("/app/ingest");
}

async function importTextAction(formData: FormData) {
  "use server";

  await importTextSource(
    {
      title: String(formData.get("title") ?? ""),
      locator: String(formData.get("locator") ?? "").trim() || undefined,
      body: String(formData.get("body") ?? ""),
      excerpt: String(formData.get("excerpt") ?? "").trim() || undefined,
    },
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

  await importPdfSource(
    file,
    String(formData.get("title") ?? "").trim() || undefined,
    String(formData.get("locator") ?? "").trim() || undefined,
  );
  revalidatePath("/app");
  revalidatePath("/app/raw");
  revalidatePath("/app/ingest");
}

export default async function RawPage() {
  const sources = await getRawSources();
  const pending = sources.filter((source) => source.status === "RAW" || source.status === "INGEST_PENDING");
  const recentSources = sources.slice(0, 5);

  return (
    <PageShell
      eyebrow="raw"
      title="原始材料 vault"
      description={`raw/ 是所有网页、PDF 和迁移旧笔记的入口。当前 ${pending.length} 条材料等待 ingest 编译。AI 只能提出 ingest 提案，不能直接写入 wiki。`}
    >
      <div className="mt-8">
        <RawImportPanel webAction={importWebAction} textAction={importTextAction} pdfAction={importPdfAction} />
      </div>

      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">最近资料</div>
          {sources.length > 5 && (
            <span className="text-xs text-ink-muted">显示最近 5 条，共 {sources.length} 条</span>
          )}
        </div>

        <div className="space-y-4">
          {recentSources.length > 0 ? (
            recentSources.map((source) => <SourceCard key={source.id} source={source} />)
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
      </div>
    </PageShell>
  );
}
