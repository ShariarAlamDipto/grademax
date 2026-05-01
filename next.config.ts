import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: false,
  serverExternalPackages: [
    "canvas",
    "@xenova/transformers",
    "pdf-to-png-converter",
    "sharp",
  ],
  experimental: {
    optimizePackageImports: ["recharts", "@supabase/supabase-js", "pdf-lib", "zod"],
  },
  compress: true,
  productionBrowserSourceMaps: false,
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 31536000,
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
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://va.vercel-scripts.com https://vercel.live",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' data: https://fonts.gstatic.com",
              "img-src 'self' data: blob: https://lh3.googleusercontent.com https://*.supabase.co https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev",
              "worker-src 'self' blob:",
              "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev https://vitals.vercel-insights.com https://va.vercel-scripts.com https://accounts.google.com https://*.googleapis.com",
              "frame-src 'self' blob: https://accounts.google.com https://*.supabase.co https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self' https://accounts.google.com",
            ].join("; "),
          },
        ],
      },
      {
        source: "/icon.svg",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
      {
        source: "/favicon.ico",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
      // Cache static SEO pages for better Core Web Vitals
      {
        source: "/:path(edexcel-past-papers|edexcel-igcse-past-papers|edexcel-a-level-past-papers|edexcel-worksheets|subjects|about|privacy|terms|contact)",
        headers: [
          { key: "Cache-Control", value: "public, s-maxage=3600, stale-while-revalidate=86400" },
        ],
      },
      // Cache all past-papers routes at the CDN edge (ISR revalidates at origin)
      {
        source: "/past-papers/:path*",
        headers: [
          { key: "Cache-Control", value: "public, s-maxage=3600, stale-while-revalidate=86400" },
        ],
      },
    ];
  },
  async redirects() {
    return [
      // Catch common misspellings & alternate search patterns
      { source: "/pastpapers", destination: "/past-papers", permanent: true },
      { source: "/past_papers", destination: "/past-papers", permanent: true },
      { source: "/worksheets", destination: "/edexcel-worksheets", permanent: true },
      { source: "/worksheet-generator", destination: "/generate", permanent: true },
      // Redirect trailing slashes for consistency
      { source: "/:path+/", destination: "/:path+", permanent: true },
    ];
  },
};

export default nextConfig;
