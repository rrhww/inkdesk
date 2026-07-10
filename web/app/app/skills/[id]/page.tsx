import { notFound } from "next/navigation";

import { PanelCard } from "@/components/ui/panel-card";
import { StatusPill } from "@/components/ui/status-pill";
import { PageShell } from "@/components/workbench/page-shell";
import { getSkillDetail } from "@/lib/research";
import type { SkillValidationFinding } from "@/lib/types";

type SkillDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

function findingTone(severity: string): "warm" | "neutral" {
  return severity === "error" ? "warm" : "neutral";
}

function FindingRow({ finding }: { finding: SkillValidationFinding }) {
  return (
    <div className="rounded-[22px] bg-ink-low px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill tone={findingTone(finding.severity)}>{finding.severity}</StatusPill>
        <StatusPill tone="neutral">{finding.code}</StatusPill>
      </div>
      <div className="mt-2 text-sm leading-7 text-ink-text">{finding.message}</div>
      <div className="mt-1 text-xs text-ink-muted">{finding.path}</div>
    </div>
  );
}

function FileContentBlock({ label, content }: { label: string; content: string }) {
  if (!content.trim()) {
    return null;
  }
  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{label}</div>
      <pre className="mt-4 max-h-[600px] overflow-auto rounded-[18px] bg-ink-low p-4 text-sm leading-6 text-ink-text">
{content}
      </pre>
    </PanelCard>
  );
}

function ResourceList({
  label,
  files,
}: {
  label: string;
  files: Record<string, string>;
}) {
  const entries = Object.entries(files);
  if (entries.length === 0) {
    return null;
  }
  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{label}</div>
      <div className="mt-4 space-y-4">
        {entries.map(([filename, content]) => (
          <div key={filename}>
            <div className="mb-2 font-headline text-sm font-bold text-ink-primary">{filename}</div>
            <pre className="max-h-[400px] overflow-auto rounded-[18px] bg-ink-low p-4 text-sm leading-6 text-ink-text">
{content}
            </pre>
          </div>
        ))}
      </div>
    </PanelCard>
  );
}

export default async function SkillDetailPage({ params }: SkillDetailPageProps) {
  const { id } = await params;
  const skill = await getSkillDetail(id).catch(() => null);

  if (!skill) {
    notFound();
  }

  const contract = skill.contract;
  const errorFindings = skill.validationFindings.filter((f) => f.severity === "error");
  const warningFindings = skill.validationFindings.filter((f) => f.severity === "warning");

  return (
    <PageShell eyebrow="skill detail" title={skill.name} description={skill.summary}>
      <div className="mt-4 flex flex-wrap items-center gap-2 px-1">
        <StatusPill tone={skill.valid ? "primary" : "warm"}>{skill.valid ? "valid" : "invalid"}</StatusPill>
        <StatusPill tone="soft">{skill.status}</StatusPill>
        <StatusPill tone="neutral">{skill.category}</StatusPill>
        <StatusPill tone="neutral">{skill.kind}</StatusPill>
        <StatusPill tone="neutral">{`v${skill.version}`}</StatusPill>
      </div>

      {skill.path ? <p className="mt-3 px-1 text-sm text-ink-muted">{skill.path}</p> : null}

      {/* Validation Findings */}
      {skill.validationFindings.length > 0 ? (
        <PanelCard className="mt-8 p-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">validation findings</div>
          <h2 className="mt-3 font-headline text-2xl font-bold tracking-tight text-ink-text">
            {errorFindings.length > 0
              ? `${errorFindings.length} 个 error · ${warningFindings.length} 个 warning`
              : `${warningFindings.length} 个 warning`}
          </h2>
          <div className="mt-5 space-y-3">
            {skill.validationFindings.map((finding, idx) => (
              <FindingRow key={`${finding.code}-${idx}`} finding={finding} />
            ))}
          </div>
        </PanelCard>
      ) : null}

      {/* Contract Summary */}
      <PanelCard className="mt-8 p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">contract</div>
        <div className="mt-5 grid gap-6 lg:grid-cols-2">
          <div>
            <div className="text-sm font-bold text-ink-text">Inputs</div>
            <div className="mt-2 space-y-2">
              {contract.inputs.length > 0 ? (
                contract.inputs.map((input) => (
                  <div key={input.name} className="rounded-[18px] bg-ink-low px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ink-text">{input.name}</span>
                      {input.required ? <StatusPill tone="warm">required</StatusPill> : null}
                    </div>
                    <div className="mt-1 text-xs text-ink-muted">{input.constraints || input.type}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-ink-muted">无输入声明</div>
              )}
            </div>
          </div>

          <div>
            <div className="text-sm font-bold text-ink-text">Outputs</div>
            <div className="mt-2 space-y-2">
              {contract.outputs.length > 0 ? (
                contract.outputs.map((output, idx) => (
                  <div key={`${output.type}-${idx}`} className="rounded-[18px] bg-ink-low px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ink-text">{output.type}</span>
                      {output.needsReview ? <StatusPill tone="soft">needs review</StatusPill> : null}
                    </div>
                    <div className="mt-1 text-xs text-ink-muted">{output.location}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-ink-muted">无输出声明</div>
              )}
            </div>
          </div>
        </div>

        {/* Hard Gates */}
        {contract.hardGates.length > 0 ? (
          <div className="mt-6">
            <div className="text-sm font-bold text-ink-text">Hard Gates</div>
            <div className="mt-2 space-y-2">
              {contract.hardGates.map((gate) => (
                <div key={gate.id} className="rounded-[18px] bg-ink-low px-4 py-3">
                  <div className="flex items-center gap-2">
                    <StatusPill tone="neutral">{gate.kind}</StatusPill>
                    <span className="text-sm font-semibold text-ink-text">{gate.id}</span>
                  </div>
                  <div className="mt-1 text-xs text-ink-muted">{gate.on_failure}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* Write Policy + Capabilities */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div>
            <div className="text-sm font-bold text-ink-text">Write Policy</div>
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusPill tone="neutral">{`canonicalWiki: ${contract.writePolicy.canonicalWiki}`}</StatusPill>
              <StatusPill tone="neutral">{`runArtifacts: ${contract.writePolicy.runArtifacts}`}</StatusPill>
              <StatusPill tone="neutral">{`codeRepository: ${contract.writePolicy.codeRepository}`}</StatusPill>
            </div>
          </div>
          <div>
            <div className="text-sm font-bold text-ink-text">Capabilities</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {contract.capabilities.length > 0 ? (
                contract.capabilities.map((cap) => <StatusPill key={cap} tone="soft">{cap}</StatusPill>)
              ) : (
                <span className="text-sm text-ink-muted">无</span>
              )}
            </div>
          </div>
        </div>

        {/* Next Skills */}
        {contract.nextSkills.length > 0 ? (
          <div className="mt-6">
            <div className="text-sm font-bold text-ink-text">Next Skills</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {contract.nextSkills.map((ref) => (
                <StatusPill key={ref.skillId} tone="primary">{ref.skillId}</StatusPill>
              ))}
            </div>
          </div>
        ) : null}
      </PanelCard>

      {/* SKILL.md */}
      <div className="mt-8">
        <FileContentBlock label="SKILL.md" content={skill.skillMd} />
      </div>

      {/* Contract JSON */}
      <div className="mt-6">
        <FileContentBlock
          label="contract.json"
          content={JSON.stringify(contract, null, 2)}
        />
      </div>

      {/* References + Templates + Agents */}
      <div className="mt-6 space-y-6">
        <ResourceList label="references" files={skill.references} />
        <ResourceList label="templates" files={skill.templates} />
        <ResourceList label="agents" files={skill.agents} />
      </div>
    </PageShell>
  );
}
