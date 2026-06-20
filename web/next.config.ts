import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  generateBuildId: async () => `inkdesk-${Date.now().toString(36)}`,
  async rewrites() {
    const apiBaseUrl = process.env.INKDESK_API_BASE_URL || "http://localhost:8300";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
