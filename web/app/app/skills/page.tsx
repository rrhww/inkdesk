import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { PanelCard } from "@/components/ui/panel-card";
import { StatusPill } from "@/components/ui/status-pill";
import { PageShell } from "@/components/workbench/page-shell";
import { getSkills } from "@/lib/research";
import type { SkillSummaryEntry } from "@/lib/types";

function statusTone(status: string): "primary" | "soft" | "neutral" | "warm" {
  if (status === "active") return "primary";
  if (status === "draft") return "soft";
  return "neutral";
}

function validTone(valid: boolean): "primary" | "warm" {
  return valid ? "primary" : "warm";
}

function SkillCard({ skill }: { skill: SkillSummaryEntry }) {
  return (
    <Link href={`/app/skills/${skill.name}`} className="block">
      <PanelCard className="p-6 transition-shadow hover:shadow-md">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone={statusTone(skill.status)}>{skill.status}</StatusPill>
          <StatusPill tone="neutral">{skill.category}</StatusPill>
          <StatusPill tone="neutral">{skill.kind}</StatusPill>
          <StatusPill tone={validTone(skill.valid)}>{skill.valid ? "valid" : "invalid"}</StatusPill>
        </div>
        <h3 className="mt-4 font-headline text-2xl font-bold tracking-tight text-ink-text">
          {skill.name}
        </h3>
        <p className="mt-2 text-sm leading-7 text-ink-muted">{skill.summary}</p>
        <div className="mt-4 flex items-center gap-4 text-xs text-ink-muted">
          <span>{`v${skill.version}`}</span>
          <span>{skill.contractId}</span>
        </div>
      </PanelCard>
    </Link>
  );
}

export default async function SkillsPage() {
  const summary = await getSkills();

  return (
    <PageShell
      eyebrow="skills"
      title="Skill 工作台"
      description="vault/skills/ 下的专家技能包。每个 Skill 包含 SKILL.md、contract.json、references 和 templates，由 Registry 发现并校验。"
    >
      <PanelCard className="mt-8 p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">registry 概览</div>
        <h2 className="mt-3 font-headline text-3xl font-extrabold tracking-tight text-ink-text">
          {summary.total > 0
            ? `${summary.total} 个 Skill · ${summary.valid} 个有效`
            : "还没有注册的 Skill"}
        </h2>
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <StatusPill tone="primary">{`${summary.valid} valid`}</StatusPill>
          {summary.invalid > 0 ? <StatusPill tone="warm">{`${summary.invalid} invalid`}</StatusPill> : null}
          <StatusPill tone="soft">{`${summary.byStatus.draft} draft`}</StatusPill>
          <StatusPill tone="primary">{`${summary.byStatus.active} active`}</StatusPill>
          {summary.byStatus.deprecated > 0 ? (
            <StatusPill tone="neutral">{`${summary.byStatus.deprecated} deprecated`}</StatusPill>
          ) : null}
        </div>
      </PanelCard>

      <div className="mt-8 grid gap-4 xl:grid-cols-2">
        {summary.skills.length > 0 ? (
          summary.skills.map((skill) => <SkillCard key={skill.name} skill={skill} />)
        ) : (
          <EmptyState
            eyebrow="skills empty"
            title="vault/skills/ 下没有可发现的 Skill"
            description="Skill package 需要同时包含 SKILL.md 和 contract.json 才能被 Registry 发现。请检查 vault 目录配置。"
          />
        )}
      </div>
    </PageShell>
  );
}
