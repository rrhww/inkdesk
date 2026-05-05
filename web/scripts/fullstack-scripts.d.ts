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
  export function resolveApiBaseUrl(options?: {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
  }): string | undefined;
  export function probeTcpPort(host: string, port: number, timeoutMs?: number): Promise<boolean>;
  export function checkCommand(command: string, args?: string[]): Promise<boolean>;
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
  export function waitForBackendReady(
    apiBaseUrl: string,
    options?: {
      timeoutMs?: number;
      intervalMs?: number;
      log?: ((message: string) => void) | undefined;
    },
    implementations?: {
      fetchImpl?: typeof fetch;
      probeTcpPort?: (host: string, port: number, timeoutMs?: number) => Promise<boolean>;
      checkCommand?: (command: string, args?: string[]) => Promise<boolean>;
    }
  ): Promise<void>;
}

declare module "@/scripts/run-fullstack-e2e.mjs" {
  export function buildPlaywrightCommand(options?: {
    cwd?: string;
  }): {
    command: string;
    args: string[];
  };
}
