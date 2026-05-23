/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so nginx serves the built files directly. No Node on server.
  output: 'export',
  // Mounted at /inbox-v2 initially, side-by-side with Streamlit at /inbox.
  basePath: '/inbox-v2',
  trailingSlash: true,
  images: { unoptimized: true },  // export mode doesn't run the Image Optimization API
  // Skip type checking + linting during build for hackathon speed.
  // Errors caught during `next dev` instead.
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
};

module.exports = nextConfig;
