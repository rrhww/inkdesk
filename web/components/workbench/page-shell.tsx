import type { ReactNode } from "react";

import { SectionHeading } from "@/components/ui/section-heading";

type PageShellProps = {
  eyebrow: string;
  title: string;
  description?: string;
  children: ReactNode;
};

export function PageShell({ eyebrow, title, description, children }: PageShellProps) {
  return (
    <main className="mx-auto max-w-shell px-5 py-8 lg:px-8 lg:py-9">
      <SectionHeading eyebrow={eyebrow} title={title} description={description} />
      <div className="mt-6 lg:mt-7">{children}</div>
    </main>
  );
}
