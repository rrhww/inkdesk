import { PanelCard } from "@/components/ui/panel-card";

type StatCardProps = {
  eyebrow: string;
  value: string | number;
  detail: string;
};

export function StatCard({ eyebrow, value, detail }: StatCardProps) {
  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{eyebrow}</div>
      <div className="mt-4 font-headline text-3xl font-extrabold tracking-tight text-ink-text">{value}</div>
      <div className="mt-2 text-sm text-ink-muted">{detail}</div>
    </PanelCard>
  );
}
