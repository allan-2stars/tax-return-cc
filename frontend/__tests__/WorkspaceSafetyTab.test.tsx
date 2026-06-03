import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WorkspaceSafetyTab from '@/components/settings/WorkspaceSafetyTab'
import * as recoveryApi from '@/lib/api/recovery'

jest.mock('@/lib/api/recovery')

const mockedRecovery = recoveryApi as jest.Mocked<typeof recoveryApi>

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  jest.clearAllMocks()
  mockedRecovery.getRecoverySafetyStatus.mockResolvedValue({
    data: {
      status: 'ok',
      data: {
        status: 'healthy',
        last_backup_at: '2026-06-02T10:00:00Z',
        last_verified_at: '2026-06-02T10:01:00Z',
        requires_backup_before_dangerous_action: true,
        policy_window_hours: 24,
      },
    },
  } as Awaited<ReturnType<typeof recoveryApi.getRecoverySafetyStatus>>)
})

describe('WorkspaceSafetyTab', () => {
  it('renders backup safety status and non-mutating restore preview copy', async () => {
    wrap(<WorkspaceSafetyTab />)

    expect(await screen.findByText(/workspace safety/i)).toBeInTheDocument()
    expect(await screen.findByText(/healthy/i)).toBeInTheDocument()
    expect(screen.getByText(/backups are encrypted/i)).toBeInTheDocument()
    expect(screen.getByText(/recovery key is required for portable restore/i)).toBeInTheDocument()
    expect(screen.getByText(/destructive workspace actions require/i)).toBeInTheDocument()
    expect(screen.getByText(/restore preview checks a backup and does not change data/i)).toBeInTheDocument()
  })

  it('renders backup action success', async () => {
    mockedRecovery.createBackup.mockResolvedValue({
      data: {
        status: 'ok',
        data: {
          backup_id: 'backup-123',
          status: 'created',
          created_at: '2026-06-02T10:02:00Z',
          filename: 'backup-123.trb',
          path: '/tmp/backup-123.trb',
          manifest_summary: {},
          verification: { status: 'pass', errors: [], warnings: [] },
        },
      },
    } as Awaited<ReturnType<typeof recoveryApi.createBackup>>)

    wrap(<WorkspaceSafetyTab />)

    fireEvent.click(await screen.findByRole('button', { name: /backup workspace/i }))

    expect(await screen.findByText(/backup created/i)).toBeInTheDocument()
    expect(screen.getByText(/backup-123/i)).toBeInTheDocument()
  })

  it('renders backup action failure', async () => {
    mockedRecovery.createBackup.mockRejectedValue(new Error('failed'))

    wrap(<WorkspaceSafetyTab />)

    fireEvent.click(await screen.findByRole('button', { name: /backup workspace/i }))

    expect(await screen.findByText(/backup failed/i)).toBeInTheDocument()
  })

  it('renders recovery key verification success and failure', async () => {
    mockedRecovery.verifyRecoveryKey
      .mockResolvedValueOnce({
        data: {
          status: 'ok',
          data: {
            status: 'ok',
            verified: true,
            verified_at: '2026-06-02T10:03:00Z',
          },
        },
      } as Awaited<ReturnType<typeof recoveryApi.verifyRecoveryKey>>)
      .mockRejectedValueOnce(new Error('invalid'))

    wrap(<WorkspaceSafetyTab />)

    fireEvent.change(await screen.findByLabelText(/^recovery key$/i), {
      target: { value: 'valid-key' },
    })
    fireEvent.click(screen.getByRole('button', { name: /verify recovery key/i }))

    expect(await screen.findByText(/recovery key verified/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/^recovery key$/i), {
      target: { value: 'bad-key' },
    })
    fireEvent.click(screen.getByRole('button', { name: /verify recovery key/i }))

    expect(await screen.findByText(/recovery key verification failed/i)).toBeInTheDocument()
  })

  it('renders restore preview result', async () => {
    mockedRecovery.previewRestore.mockResolvedValue({
      data: {
        status: 'ok',
        data: {
          status: 'ok',
          preview_id: 'preview-123',
          backup_id: 'backup-123',
          workspace_id: 'ws-123',
          financial_year: '2025-26',
          created_at: '2026-06-02T10:04:00Z',
          encryption_mode: 'recovery_key_derived',
          record_counts: { tax_events: 3 },
          included_sections: ['tax_events', 'review_items'],
          compatibility: { status: 'compatible', blockers: [], warnings: ['Existing workspace found.'] },
          blockers: [],
          warnings: ['Existing workspace found.'],
          can_restore: true,
        },
      },
    } as Awaited<ReturnType<typeof recoveryApi.previewRestore>>)

    wrap(<WorkspaceSafetyTab />)

    fireEvent.change(await screen.findByLabelText(/backup id for restore preview/i), {
      target: { value: 'backup-123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /preview restore/i }))

    expect(await screen.findByText(/can restore/i)).toBeInTheDocument()
    expect(screen.getByText(/existing workspace found/i)).toBeInTheDocument()
    expect(screen.getAllByText(/preview only; no data is changed/i).length).toBeGreaterThan(0)
  })

  it('renders backup verification success', async () => {
    mockedRecovery.verifyBackup.mockResolvedValue({
      data: {
        status: 'ok',
        data: {
          backup_id: 'backup-123',
          status: 'verified',
          manifest_summary: {},
          verification: { status: 'pass', errors: [], warnings: [] },
        },
      },
    } as Awaited<ReturnType<typeof recoveryApi.verifyBackup>>)

    wrap(<WorkspaceSafetyTab />)

    fireEvent.change(await screen.findByLabelText(/backup id to verify/i), {
      target: { value: 'backup-123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /verify backup/i }))

    await waitFor(() => {
      expect(screen.getByText(/backup verified/i)).toBeInTheDocument()
    })
  })
})
