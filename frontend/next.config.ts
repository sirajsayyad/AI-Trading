import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "172.18.9.62"],
  experimental: { proxyTimeout: 210000 },
  async rewrites() {
    return [{
      source: "/api/:path*",
      destination: `${process.env.API_URL || "http://127.0.0.1:8000"}/:path*`,
    }];
  },
};

export default nextConfig;
