import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [
    "canvas",
    "@xenova/transformers",
    "pdf-to-png-converter",
    "sharp",
  ],
  experimental: {
    optimizePackageImports: ["recharts"],
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
      {
        protocol: "https",
        hostname: "*.supabase.co",
      },
    ],
  },
};

export default nextConfig;
