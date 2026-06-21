import type { ReactNode } from "react";

import { AppChrome } from "@/components/app-chrome";
import { getDevRuns, getResearchDashboard } from "@/lib/research";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const [snapshot, devRuns] = await Promise.all([
    getResearchDashboard(),
    getDevRuns(),
  ]);

  return (
    <AppChrome snapshot={snapshot} devRuns={devRuns}>
      {children}
    </AppChrome>
  );
}
