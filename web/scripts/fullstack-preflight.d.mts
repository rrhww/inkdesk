export type LocalDiagnostics =
  | {
      isLocal: false;
    }
  | {
      isLocal: true;
      backendHost: string;
      backendPort: number;
      backendReachable: boolean;
      postgresReachable: boolean;
      minioReachable: boolean;
      dockerAvailable: boolean;
    };

export type ProbeTcpPort = (host: string, port: number, timeoutMs?: number) => Promise<boolean>;

export type CheckCommand = (command: string, args?: string[]) => Promise<boolean>;

export function readEnvFileValue(filePath: string, key: string): string | undefined;

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
  dependencies?: {
    probeTcpPort?: ProbeTcpPort;
    checkCommand?: CheckCommand;
  }
): Promise<LocalDiagnostics>;

export function buildBackendUnavailableMessage(options: {
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
    log?: ((message: string) => void) | false | null;
  },
  dependencies?: {
    fetchImpl?: typeof fetch;
    probeTcpPort?: ProbeTcpPort;
    checkCommand?: CheckCommand;
  }
): Promise<void>;
