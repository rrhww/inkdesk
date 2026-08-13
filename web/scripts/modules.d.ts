declare module "@/scripts/fullstack-preflight.mjs" {
  export type LocalDiagnostics = {
    isLocal: boolean;
    backendHost?: string;
    backendPort?: number;
    backendReachable?: boolean;
    postgresReachable?: boolean;
    minioReachable?: boolean;
    dockerAvailable?: boolean;
  };

  export function normalizeApiBaseUrl(value?: string): string | undefined;
  export function toHealthUrl(apiBaseUrl: string): string;
  export function collectLocalDiagnostics(
    apiBaseUrl: string,
    options?: {
      probeTcpPort?: (host: string, port: number, timeoutMs?: number) => Promise<boolean>;
      checkCommand?: (command: string, args?: string[]) => Promise<boolean>;
    }
  ): Promise<LocalDiagnostics>;
  export function buildBackendUnavailableMessage(input: {
    apiBaseUrl: string;
    healthUrl: string;
    lastStatus?: number;
    lastError?: string;
    diagnostics?: LocalDiagnostics;
  }): string;
}

declare module "@/scripts/run-fullstack-e2e.mjs" {
  export function buildPlaywrightCommand(options?: {
    cwd?: string;
  }): {
    command: string;
    args: string[];
  };
}
