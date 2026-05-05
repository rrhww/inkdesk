import Link from "next/link";

import type { PublicProject } from "@/lib/types";

type PublicProjectCardProps = {
  project: PublicProject;
  featured?: boolean;
};

export function PublicProjectCard({ project, featured = false }: PublicProjectCardProps) {
  return (
    <Link href={`/projects/${project.slug}`} className={featured ? "project-spotlight block" : "project-status-item block"}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="public-eyebrow">{project.kind}</div>
        <span className="rounded-full border border-ink-primary/15 bg-ink-primarySoft px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-ink-primary">
          {project.statusLabel}
        </span>
      </div>
      <h3 className={`font-headline font-bold tracking-tight text-ink-text ${featured ? "mt-4 text-4xl" : "mt-3 text-2xl"}`}>{project.title}</h3>
      <p className={`text-ink-muted ${featured ? "mt-4 text-[1.05rem] leading-8" : "mt-3 text-sm leading-7"}`}>{project.summary}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {project.stack.slice(0, featured ? 4 : 3).map((entry) => (
          <span key={entry} className="public-chip">
            {entry}
          </span>
        ))}
      </div>
      {featured ? (
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {project.highlights.slice(0, 3).map((entry) => (
            <div key={entry} className="rounded-[20px] border border-black/5 bg-white/70 px-4 py-4 text-sm leading-7 text-ink-muted">
              {entry}
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-6 border-t border-black/5 pt-4 text-sm text-ink-muted">{project.updatedAt}</div>
    </Link>
  );
}
