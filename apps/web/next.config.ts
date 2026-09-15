import type { NextConfig } from "next";

// Allow `next/image` to optimize remote previews coming from Backblaze B2.
// Presigned download URLs use the bucket-specific S3 hostname pattern:
//   <bucket>.s3.<region>.backblazeb2.com    (path-style and virtual-host)
//   s3.<region>.backblazeb2.com             (path-style)
// One wildcard covers every region + bucket, so this config drops in
// without per-deployment tweaks.
const nextConfig: NextConfig = {
  transpilePackages: ["@carla-sensor-data-lake/shared"],
  // Next 16's dev server blocks cross-origin requests to dev-only assets
  // (e.g. _next/static chunks) unless the request Host is explicitly
  // allowed. This app's own Playwright config (and macOS users generally)
  // drive the dev server via `127.0.0.1` rather than `localhost`, because
  // macOS can resolve `localhost` to `::1` and miss a v4-only listener.
  // Without this, React never hydrates on 127.0.0.1: every _next/static
  // request gets rejected and pages stay on their loading skeletons.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.backblazeb2.com",
      },
    ],
  },
};

export default nextConfig;
