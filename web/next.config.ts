import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  generateBuildId: async () => `inkdesk-${Date.now().toString(36)}`
};

export default nextConfig;
