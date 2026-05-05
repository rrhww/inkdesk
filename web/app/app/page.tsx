import { ResearchDashboardView } from "@/components/workbench/research-dashboard";
import { getRequestOwnerSession } from "@/lib/request-owner-session";
import { getResearchDashboard } from "@/lib/research";

export default async function WorkbenchPage() {
  const ownerSession = await getRequestOwnerSession();

  return <ResearchDashboardView snapshot={await getResearchDashboard(ownerSession)} />;
}
