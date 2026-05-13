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
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <SectionHeading eyebrow={eyebrow} title={title} description={description} />
      {children}
    </main>
  );
}
