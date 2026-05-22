import client from './client'
import type {
  ApiResponse,
  AiUsageData,
  StorageUsageData,
  AboutData,
  WorkspaceListData,
  WorkspaceInfo,
  RecoveryKeyData,
} from './types'

export const getAiUsage = () =>
  client.get<ApiResponse<AiUsageData>>('/api/v1/settings/ai-usage')

export const getStorageUsage = () =>
  client.get<ApiResponse<StorageUsageData>>('/api/v1/settings/storage-usage')

export const getAbout = () =>
  client.get<ApiResponse<AboutData>>('/api/v1/settings/about')

export const exportDiagnosticLog = async (): Promise<void> => {
  const response = await client.get('/api/v1/settings/diagnostic-log', {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'diagnostic.json'
  a.click()
  URL.revokeObjectURL(url)
}

export const changePassword = (currentPassword: string, newPassword: string) =>
  client.post('/api/v1/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })

export const regenerateRecoveryKey = (password: string) =>
  client.post<ApiResponse<RecoveryKeyData>>('/api/v1/auth/recovery-key/regenerate', {
    password,
  })

export const listWorkspaces = () =>
  client.get<ApiResponse<WorkspaceListData>>('/api/v1/workspaces')

export const updateWorkspaceName = (id: string, name: string) =>
  client.patch<ApiResponse<WorkspaceInfo>>(`/api/v1/workspaces/${id}`, { name })
