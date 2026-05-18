/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Required for the two-stage Dockerfile (Stage 2 copies .next/standalone/)
  output: 'standalone',

  // next-pwa setup (install `next-pwa` package to enable):
  // const withPWA = require('next-pwa')({
  //   dest: 'public',
  //   disable: process.env.NODE_ENV !== 'production',
  // })
  // module.exports = withPWA(nextConfig)
}

module.exports = nextConfig
