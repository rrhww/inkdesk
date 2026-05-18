type SectionHeadingProps = {
  eyebrow: string;
  title: string;
  description?: string;
};

export function SectionHeading({ eyebrow, title, description }: SectionHeadingProps) {
  return (
    <div className="max-w-4xl">
      <div className="slip">{eyebrow}</div>
      <h2 className="mt-4 font-headline text-[clamp(2rem,4vw,3.15rem)] font-bold leading-[1.08] tracking-[-0.03em] text-ink-text">
        {title}
      </h2>
      {description ? <p className="mt-4 max-w-3xl text-sm leading-8 text-ink-muted">{description}</p> : null}
    </div>
  );
}
