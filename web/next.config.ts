import type { NextConfig } from "next";

const projectRoot = process.cwd();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: projectRoot,
  turbopack: {
    root: projectRoot
  },
  experimental: {
    cpus: 2,
    staticGenerationMaxConcurrency: 2
  },
  generateBuildId: async () => `inkvault-${Date.now().toString(36)}`
};

export default nextConfig;
