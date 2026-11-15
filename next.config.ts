import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow images from HuggingFace
  images: {
    remotePatterns: [{ hostname: "huggingface.co" }],
  },
};

export default nextConfig;
