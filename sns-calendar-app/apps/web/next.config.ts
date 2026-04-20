import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@sns-calendar/shared-types", "@sns-calendar/ui"],
};

export default nextConfig;

