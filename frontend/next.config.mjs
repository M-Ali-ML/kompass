import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow an isolated build/dev output dir (used by the E2E suite so its dev
  // server lock doesn't collide with a developer's running `next dev`).
  distDir: process.env.NEXT_DIST_DIR || '.next',
  // Pin the workspace root to this app so Next never mis-detects it from a
  // stray lockfile higher up the tree (which silently breaks module resolution).
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
