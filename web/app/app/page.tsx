import { AskWorkspacePage } from "@/components/workbench/ask-workspace";
import { getVaultStatus } from "@/lib/research";
import { VaultInitCard } from "@/components/workbench/vault-init-card";
import { cookies } from "next/headers";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";

type WorkbenchPageProps = {
  searchParams: Promise<{
    q?: string;
    topicId?: string;
    mode?: string;
    continueFromAskTurnId?: string;
  }>;
};

export default async function WorkbenchPage({ searchParams }: WorkbenchPageProps) {
  const cookieStore = await cookies();
  const ownerSession = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

  if (ownerSession) {
    const status = await getVaultStatus(ownerSession).catch(() => null);
    if (status && !status.vaultType) {
      return <VaultInitCard />;
    }
  }

  return await AskWorkspacePage({ searchParams });
}
