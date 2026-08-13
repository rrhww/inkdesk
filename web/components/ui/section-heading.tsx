type SectionHeadingProps = {
  eyebrow: string;
  title: string;
  description?: string;
};

export function SectionHeading({ eyebrow, title, description }: SectionHeadingProps) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">{eyebrow}</div>
      <h2 className="mt-3 font-headline text-4xl font-extrabold tracking-tight text-ink-text">{title}</h2>
      {description ? <p className="mt-4 max-w-3xl text-sm leading-7 text-ink-muted">{description}</p> : null}
    </div>
  );
}
