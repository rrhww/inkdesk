import { DevRunConsole } from "@/components/workbench/dev-run-console";
import { getVaultStatus } from "@/lib/research";
import { VaultInitCard } from "@/components/workbench/vault-init-card";

export default async function WorkbenchPage() {
  const status = await getVaultStatus().catch(() => null);
  if (status && !status.vaultType) {
    return <VaultInitCard />;
  }

  return <DevRunConsole />;
}
