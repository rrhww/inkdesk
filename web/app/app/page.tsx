import { AgentConsole } from "@/components/workbench/agent-console";
import { getWorkbenchSnapshot } from "@/lib/home";
import { getRequestOwnerSession } from "@/lib/request-owner-session";

export default async function WorkbenchPage() {
  const ownerSession = await getRequestOwnerSession();

  return <AgentConsole snapshot={await getWorkbenchSnapshot(ownerSession)} />;
}
