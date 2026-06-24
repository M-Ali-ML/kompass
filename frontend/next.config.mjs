/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow an isolated build/dev output dir (used by the E2E suite so its dev
  // server lock doesn't collide with a developer's running `next dev`).
  distDir: process.env.NEXT_DIST_DIR || '.next',
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
