import client from './client'
import type {
  ApiResponse,
  RecoveryBackupData,
  RecoveryEncryptionMode,
  RecoveryKeyVerificationData,
  RecoveryRestorePreviewData,
  RecoverySafetyStatusData,
  RecoveryVerifyBackupData,
} from './types'

export const getRecoverySafetyStatus = () =>
  client.get<ApiResponse<RecoverySafetyStatusData>>('/api/v1/recovery/safety-status')

export const createBackup = (payload?: {
  encryption_mode?: RecoveryEncryptionMode
  recovery_key?: string | null
}) =>
  client.post<ApiResponse<RecoveryBackupData>>('/api/v1/recovery/backups', payload ?? {})

export const verifyBackup = (backupId: string) =>
  client.post<ApiResponse<RecoveryVerifyBackupData>>('/api/v1/recovery/backups/verify', {
    backup_id: backupId,
  })

export const verifyRecoveryKey = (recoveryKey: string) =>
  client.post<ApiResponse<RecoveryKeyVerificationData>>('/api/v1/recovery/key/verify', {
    recovery_key: recoveryKey,
  })

export const previewRestore = (payload: {
  backup_id: string
  recovery_key?: string | null
}) =>
  client.post<ApiResponse<RecoveryRestorePreviewData>>('/api/v1/recovery/restore/preview', payload)
