import type { NextConfig } from "next";

// Google AdSense origins. Without these the loader in the root layout's <head>
// is blocked outright, ads never render and — because the review crawler runs
// the page — site verification fails with no visible error but a CSP console
// warning.
//
// This stays a list of Google's own origins rather than a blanket `https:`
// because ad creatives are rendered *inside* Google's cross-origin iframes,
// which carry their own policy; this document's CSP does not reach into them.
// So allowing Google here is enough to serve ads without opening the page to
// every advertiser domain on the internet.
const GOOGLE_ADS_ORIGINS = [
  "https://*.googlesyndication.com", // pagead2 (the loader), tpc (creatives)
  "https://*.doubleclick.net", // ad requests, securepubads
  "https://*.googleadservices.com",
  "https://*.googletagservices.com",
  "https://adservice.google.com",
  "https://fundingchoicesmessages.google.com", // EEA/UK consent messaging
  // Ad Traffic Quality (ep1/ep2.adtrafficquality.google) — AdSense's invalid-traffic
  // beacon. Its TLD is bare `.google`, so the `https://*.google.com` entries below
  // never matched it and every page load logged a blocked-connection CSP error.
  "https://*.adtrafficquality.google",
].join(" ");

const baseCsp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' 'unsafe-eval' https://va.vercel-scripts.com https://vercel.live ${GOOGLE_ADS_ORIGINS}`,
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' data: https://fonts.gstatic.com",
  `img-src 'self' data: blob: https://lh3.googleusercontent.com https://*.supabase.co https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev ${GOOGLE_ADS_ORIGINS} https://*.google.com https://*.gstatic.com`,
  "worker-src 'self' blob:",
  // *.r2.cloudflarestorage.com is the S3 API endpoint teachers PUT large
  // lecture files to with a presigned URL, bypassing the 4.5 MB serverless cap.
  `connect-src 'self' https://*.supabase.co wss://*.supabase.co https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev https://*.r2.cloudflarestorage.com https://vitals.vercel-insights.com https://va.vercel-scripts.com https://accounts.google.com https://*.googleapis.com ${GOOGLE_ADS_ORIGINS} https://*.google.com`,
  `frame-src 'self' blob: https://accounts.google.com https://*.supabase.co https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev ${GOOGLE_ADS_ORIGINS} https://*.google.com`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self' https://accounts.google.com",
].join("; ");

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
  // The prebuild papers-index snapshot (src/generated/papers-index.json) is read
  // with fs at runtime by on-demand past-papers renders (Cambridge deep pages),
  // so it must be traced into those function bundles. Missing file = DB fallback.
  outputFileTracingIncludes: {
    "/past-papers/**": ["./src/generated/**"],
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
            value: baseCsp,
          },
        ],
      },
      {
        source: "/api/worksheets/:path*",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Content-Security-Policy", value: baseCsp.replace("frame-ancestors 'none'", "frame-ancestors 'self'") },
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
        source: "/:path(edexcel-past-papers|edexcel-igcse-past-papers|edexcel-a-level-past-papers|edexcel-worksheets|cambridge-past-papers|cambridge-igcse-past-papers|cambridge-a-level-past-papers|subjects|about|privacy|terms|contact)",
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
