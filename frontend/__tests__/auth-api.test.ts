jest.mock('@/lib/api/client', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

import client from '@/lib/api/client'
import * as authApi from '@/lib/api/auth'

const mockPost = client.post as jest.Mock
const mockGet = client.get as jest.Mock

beforeEach(() => {
  jest.clearAllMocks()
})

describe('auth API', () => {
  it('login POSTs to /api/v1/auth/login with password', async () => {
    mockPost.mockResolvedValue({ data: { data: { workspace_id: 'ws1' } } })
    await authApi.login('secret')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/login', { password: 'secret' })
  })

  it('logout POSTs to /api/v1/auth/logout', async () => {
    mockPost.mockResolvedValue({})
    await authApi.logout()
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/logout')
  })

  it('getSession GETs /api/v1/auth/session', async () => {
    mockGet.mockResolvedValue({ data: { data: {} } })
    await authApi.getSession()
    expect(mockGet).toHaveBeenCalledWith('/api/v1/auth/session')
  })

  it('setup POSTs to /api/v1/auth/setup with password and financial_year', async () => {
    mockPost.mockResolvedValue({ data: { data: { recovery_key: 'key' } } })
    await authApi.setup('mypassword', '2024-25')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/setup', {
      password: 'mypassword',
      financial_year: '2024-25',
    })
  })

  it('setup uses default financial_year of 2024-25 when not specified', async () => {
    mockPost.mockResolvedValue({ data: { data: { recovery_key: 'key' } } })
    await authApi.setup('mypassword')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/setup', {
      password: 'mypassword',
      financial_year: '2024-25',
    })
  })

  it('setupConfirm POSTs to /api/v1/auth/setup/confirm with confirmation', async () => {
    mockPost.mockResolvedValue({})
    await authApi.setupConfirm('1234-5678')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/setup/confirm', { confirmation: '1234-5678' })
  })

  it('unlock POSTs to /api/v1/auth/unlock with password', async () => {
    mockPost.mockResolvedValue({})
    await authApi.unlock('mypassword')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/unlock', { password: 'mypassword' })
  })

  it('recover POSTs to /api/v1/auth/recover with recovery_key and new_password', async () => {
    mockPost.mockResolvedValue({})
    await authApi.recover('RECOVERY-KEY', 'newpassword')
    expect(mockPost).toHaveBeenCalledWith('/api/v1/auth/recover', {
      recovery_key: 'RECOVERY-KEY',
      new_password: 'newpassword',
    })
  })
})
