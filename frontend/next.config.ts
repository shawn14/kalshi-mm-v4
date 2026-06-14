import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",   // static export — no Node.js needed on server
  trailingSlash: true,
  // API calls go directly to FastAPI backend (same host, /api/* routes)
};

export default nextConfig;
