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
    ];
  },
};

export default nextConfig;
