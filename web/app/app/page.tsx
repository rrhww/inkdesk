import { DevRunConsole } from "@/components/workbench/dev-run-console";
import { getVaultStatus } from "@/lib/research";
import { VaultInitCard } from "@/components/workbench/vault-init-card";
import { cookies } from "next/headers";
import { OWNER_SESSION_COOKIE } from "@/lib/owner-session";

export default async function WorkbenchPage() {
  const cookieStore = await cookies();
  const ownerSession = cookieStore.get(OWNER_SESSION_COOKIE)?.value;

  if (ownerSession) {
    const status = await getVaultStatus(ownerSession).catch(() => null);
    if (status && !status.vaultType) {
      return <VaultInitCard />;
    }
  }

  return <DevRunConsole />;
}
