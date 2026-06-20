import { DevRunConsole } from "@/components/workbench/dev-run-console";
import { OWNER_SESSION_VALUE } from "@/lib/owner-session";
import { getVaultStatus } from "@/lib/research";
import { VaultInitCard } from "@/components/workbench/vault-init-card";

export default async function WorkbenchPage() {
  const status = await getVaultStatus(OWNER_SESSION_VALUE).catch(() => null);
  if (status && !status.vaultType) {
    return <VaultInitCard />;
  }

  return <DevRunConsole />;
}
