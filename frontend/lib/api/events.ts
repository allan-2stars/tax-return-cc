import client from './client'
import type { ManualEventPayload, CreateManualEventData, AttachReceiptData } from './types'

export const createManualEvent = (data: ManualEventPayload) =>
  client.post<{ data: CreateManualEventData }>('/api/v1/events/manual', data)

export const attachReceipt = (eventId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return client.post<{ data: AttachReceiptData }>(
    `/api/v1/events/${eventId}/attach-receipt`,
    form
  )
}
