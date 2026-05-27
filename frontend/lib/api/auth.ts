// frontend/lib/api/auth.ts
import client from './client'
import type { ApiResponse, LoginData, SessionData, SetupData } from './types'

export const login = (password: string) =>
  client.post<ApiResponse<LoginData>>('/api/v1/auth/login', { password })

export const logout = () =>
  client.post('/api/v1/auth/logout')

export const getSession = () =>
  client.get<ApiResponse<SessionData>>('/api/v1/auth/session')

export const setup = (password: string, financialYear: string = '2024-25') =>
  client.post<ApiResponse<SetupData>>('/api/v1/auth/setup', {
    password,
    financial_year: financialYear,
  })

export const setupConfirm = (confirmation: string) =>
  client.post('/api/v1/auth/setup/confirm', { confirmation })

export const unlock = (password: string) =>
  client.post('/api/v1/auth/unlock', { password })

export const recover = (recoveryKey: string, newPassword: string) =>
  client.post('/api/v1/auth/recover', { recovery_key: recoveryKey, new_password: newPassword })
