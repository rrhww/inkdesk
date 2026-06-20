import type { ReactNode } from "react";

import { AppChrome } from "@/components/app-chrome";
import { getDevRuns, getResearchDashboard } from "@/lib/research";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const ownerSession = OWNER_SESSION_VALUE;

  const [snapshot, devRuns] = await Promise.all([
    getResearchDashboard(ownerSession),
    getDevRuns(ownerSession),
  ]);

  return (
    <AppChrome snapshot={snapshot} devRuns={devRuns}>
      {children}
    </AppChrome>
  );
}
