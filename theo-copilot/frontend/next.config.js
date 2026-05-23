/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so nginx serves the built files directly. No Node on server.
  output: 'export',
  // Default inbox path. (Streamlit fallback is at /inbox-classic.)
  basePath: '/inbox',
  trailingSlash: true,
  images: { unoptimized: true },  // export mode doesn't run the Image Optimization API
  // Skip type checking + linting during build for hackathon speed.
  // Errors caught during `next dev` instead.
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
};

module.exports = nextConfig;
