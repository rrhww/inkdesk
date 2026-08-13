type StatusPillProps = {
  children: string;
  tone?: "primary" | "soft" | "neutral" | "warm";
};

export function StatusPill({ children, tone = "neutral" }: StatusPillProps) {
  const toneClassName =
    tone === "primary"
      ? "bg-ink-primary text-white"
      : tone === "soft"
        ? "bg-ink-primarySoft text-ink-primary"
        : tone === "warm"
          ? "bg-[#fff4ec] text-ink-tertiary"
          : "bg-white text-ink-muted";

  return <span className={`rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${toneClassName}`}>{children}</span>;
}
