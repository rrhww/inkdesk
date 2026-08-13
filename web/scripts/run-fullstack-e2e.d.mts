export function buildPlaywrightCommand(options?: {
  cwd?: string;
}): {
  command: string;
  args: string[];
};
