import type { ReactNode } from "react";

import { AppChrome } from "@/components/app-chrome";
import { getDevRuns, getResearchDashboard } from "@/lib/research";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import type { DevRunSummary, ResearchDashboard } from "@/lib/types";

export default async function AppLayout({ children }: { children: ReactNode }) {
  let snapshot: ResearchDashboard;
  let devRuns: DevRunSummary[];

  const ownerSession = OWNER_SESSION_VALUE;

  [snapshot, devRuns] = await Promise.all([
    getResearchDashboard(ownerSession),
    getDevRuns(ownerSession),
  ]);

  return (
    <AppChrome snapshot={snapshot} devRuns={devRuns}>
      {children}
    </AppChrome>
  );
}
