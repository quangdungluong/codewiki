import type { NextConfig } from 'next';

const TARGET_SERVER_BASE_URL =
  process.env.SERVER_BASE_URL || 'http://localhost:8001';

const nextConfig: NextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/lang/config',
        destination: `${TARGET_SERVER_BASE_URL}/lang/config`,
      },
      {
        source: '/api/wiki/projects',
        destination: `${TARGET_SERVER_BASE_URL}/api/processed_projects`,
      },
      {
        source: '/api/wiki_cache/:path*',
        destination: `${TARGET_SERVER_BASE_URL}/api/wiki_cache/:path*`,
      },
      {
        source: '/api/wiki/generate',
        destination: `${TARGET_SERVER_BASE_URL}/api/wiki/generate`,
      },
      {
        source: '/api/wiki/status/:path*',
        destination: `${TARGET_SERVER_BASE_URL}/api/wiki/status/:path*`,
      },
      {
        source: '/api/chat/stream',
        destination: `${TARGET_SERVER_BASE_URL}/chat/completions/stream`,
      },
    ];
  },
};

export default nextConfig;
