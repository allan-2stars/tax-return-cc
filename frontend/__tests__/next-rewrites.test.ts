/* eslint-disable @typescript-eslint/no-var-requires */

describe('next.config rewrites', () => {
  const ORIGINAL_ENV = process.env.ENVIRONMENT

  afterEach(() => {
    if (ORIGINAL_ENV === undefined) {
      delete process.env.ENVIRONMENT
    } else {
      process.env.ENVIRONMENT = ORIGINAL_ENV
    }
    jest.resetModules()
  })

  it('keeps /api/* proxy rewrites enabled in production', async () => {
    process.env.ENVIRONMENT = 'production'

    // next.config.js is CJS and wrapped by next-pwa; require at runtime.
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    const nextConfig = require('../next.config.js')
    expect(typeof nextConfig.rewrites).toBe('function')

    // eslint-disable-next-line @typescript-eslint/no-unsafe-call
    const rewrites = await nextConfig.rewrites()

    expect(rewrites).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: '/api/:path*',
          destination: 'http://backend:8000/api/:path*',
        }),
      ])
    )
  })
})

