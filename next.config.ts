import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow images from HuggingFace
  images: {
    domains: ["huggingface.co"],
  },
};

export default nextConfig;
