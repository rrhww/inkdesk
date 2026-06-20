"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PanelCard } from "@/components/ui/panel-card";
import { initializeVault } from "@/lib/research";

const PREVIEW_DIRS: Record<string, string[]> = {
  code: [
    "raw/", "wiki/", "wiki/entities/", "wiki/concepts/",
    "schema/", "skills/", "evals/", "runs/",
  ],
  general: [
    "raw/", "wiki/", "wiki/topics/", "wiki/sources/", "wiki/queries/",
    "schema/", "skills/", "evals/", "runs/",
  ],
};

const TYPE_LABELS: Record<string, { title: string; desc: string }> = {
  code: {
    title: "代码项目型",
    desc: "按实体-概念组织知识，适合有代码仓库的工程研究。",
  },
  general: {
    title: "通用知识型",
    desc: "按主题-来源-问答组织知识，适合学习笔记、阅读研究和专题探索。",
  },
};

export function VaultInitCard() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const router = useRouter();

  async function handleInit() {
    if (!selectedType) return;
    setSubmitting(true);
    setError(null);
    try {
      await initializeVault({ vaultType: selectedType });
      setDone(true);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "初始化失败，请重试。");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <PanelCard className="p-8">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">初始化完成</div>
        <h3 className="mt-4 font-headline text-3xl font-extrabold text-ink-text">知识库已就绪</h3>
        <p className="mt-4 max-w-2xl text-sm text-ink-muted">
          {selectedType === "code"
            ? "已创建代码项目型 Vault，wiki 按实体-概念组织。"
            : "已创建通用知识型 Vault，wiki 按主题-来源-问答组织。"}
          下一步：导入第一批材料。
        </p>
        <a href="/app/raw"
           className="mt-6 inline-flex rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white">
          导入首批材料
        </a>
      </PanelCard>
    );
  }

  return (
    <PanelCard className="p-8">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">知识库初始化</div>
      <h3 className="mt-4 font-headline text-3xl font-extrabold text-ink-text">选择知识库类型</h3>
      <p className="mt-4 max-w-2xl text-sm text-ink-muted">
        选择知识库结构。类型决定 wiki 子目录与 Agent 行为。初始化后仍可继续补充材料。
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4">
        {Object.entries(TYPE_LABELS).map(([key, { title, desc }]) => (
          <button key={key}
                  onClick={() => setSelectedType(key)}
                  className={`rounded-2xl border-2 p-6 text-left transition ${
                    selectedType === key
                      ? "border-ink-primary bg-ink-primarySoft"
                      : "border-ink-high bg-white hover:border-ink-line"}`}>
            <div className="font-headline text-lg font-bold text-ink-text">{title}</div>
            <div className="mt-2 text-sm text-ink-muted">{desc}</div>
          </button>
        ))}
      </div>

      {selectedType && (
        <div className="mt-6 rounded-2xl bg-ink-low p-6">
          <div className="text-xs font-semibold uppercase text-ink-muted">结构预览</div>
          <div className="mt-3 font-mono text-sm text-ink-text">
            {PREVIEW_DIRS[selectedType].map((dir) => <div key={dir}>{dir}</div>)}
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
      )}

      <button disabled={!selectedType || submitting}
              onClick={handleInit}
              className="mt-6 inline-flex rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white disabled:opacity-40">
        {submitting ? "正在初始化..." : "确认初始化"}
      </button>
    </PanelCard>
  );
}
