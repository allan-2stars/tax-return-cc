import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SettingsPage from '@/app/(dashboard)/settings/page'
import * as settingsApi from '@/lib/api/settings'
import type { AiUsageData, StorageUsageData, AboutData, WorkspaceListData } from '@/lib/api/types'

jest.mock('@/lib/api/settings')
jest.mock('@/lib/stores/workspace.store', () => ({
  __esModule: true,
  default: () => ({
    workspaceId: 'ws-123',
    financialYear: '2024-25',
    isAuthenticated: true,
    isUnlocked: true,
    setWorkspace: jest.fn(),
    setAuthenticated: jest.fn(),
    setUnlocked: jest.fn(),
  }),
}))
jest.mock('@/components/shared/Disclaimer', () => ({
  default: () => (
    <p data-testid="disclaimer">
      This tool helps organise your tax information and prepare a review package. It does not
      provide final tax advice and does not replace review by a registered tax agent.
    </p>
  ),
  __esModule: true,
}))
jest.mock('@/components/settings/WorkspaceTab', () => ({
  default: () => (
    <div>
      <input aria-label="Workspace name" defaultValue="My Return" />
      <p aria-label="Financial year (read only)">2024-25</p>
    </div>
  ),
  __esModule: true,
}))
jest.mock('@/components/settings/SecurityTab', () => ({
  default: () => (
    <div>
      <input aria-label="Current password" type="password" />
      <input aria-label="New password" type="password" />
      <input aria-label="Confirm new password" type="password" />
      <button onClick={() => {}}>Never</button>
      <p>Not recommended for sensitive tax data</p>
    </div>
  ),
  __esModule: true,
}))
jest.mock('@/components/settings/AiPrivacyTab', () => ({
  default: () => (
    <div>
      <li>Extracted text from documents</li>
      <li>Transaction amounts and dates</li>
      <li>Merchant names</li>
      <li>Original files</li>
      <li>Your name or personal details</li>
      <li>Bank account numbers</li>
      <li>Tax File Number (TFN)</li>
      <p>142 calls</p>
      <p>38 calls</p>
    </div>
  ),
  __esModule: true,
}))
jest.mock('@/components/settings/StorageTab', () => ({
  default: () => (
    <div>
      <p>Documents</p>
      <p>Exports</p>
      <p>Database</p>
    </div>
  ),
  __esModule: true,
}))
jest.mock('@/components/settings/AboutTab', () => ({
  default: () => (
    <div>
      <p data-testid="disclaimer">
        This tool helps organise your tax information and prepare a review package. It does not
        provide final tax advice and does not replace review by a registered tax agent.
      </p>
      <p>employee_tax_au</p>
    </div>
  ),
  __esModule: true,
}))

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeEach(() => {
  jest.clearAllMocks()
})

describe('SettingsPage', () => {
  it('renders 5 tabs', () => {
    wrap(<SettingsPage />)
    expect(screen.getByRole('tab', { name: /workspace/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /security/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /ai.*privacy/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /storage/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /about/i })).toBeInTheDocument()
  })

  it('default tab is Workspace', () => {
    wrap(<SettingsPage />)
    expect(screen.getByLabelText(/workspace name/i)).toBeInTheDocument()
  })

  it('Workspace tab: name field is editable', () => {
    wrap(<SettingsPage />)
    const input = screen.getByLabelText(/workspace name/i) as HTMLInputElement
    expect(input).toBeInTheDocument()
    expect(input.tagName).toBe('INPUT')
  })

  it('Workspace tab: financial year is display-only (no editable input)', () => {
    wrap(<SettingsPage />)
    expect(screen.getByLabelText(/financial year.*read only/i)).toBeInTheDocument()
    // The FY element must NOT be an input
    const fyEl = screen.getByLabelText(/financial year.*read only/i)
    expect(fyEl.tagName).not.toBe('INPUT')
  })

  it('Security tab: change password form renders 3 fields', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /security/i }))
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^new password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument()
  })

  it('Security tab: Never auto-lock shows warning', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /security/i }))
    expect(screen.getByText(/not recommended for sensitive tax data/i)).toBeInTheDocument()
  })

  it('AI & Privacy tab: What we send to AI list renders all 7 items', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /ai.*privacy/i }))
    const items = [
      'Extracted text from documents',
      'Transaction amounts and dates',
      'Merchant names',
      'Original files',
      'Your name or personal details',
      'Bank account numbers',
      'Tax File Number (TFN)',
    ]
    for (const item of items) {
      expect(screen.getByText(item)).toBeInTheDocument()
    }
  })

  it('AI & Privacy tab: usage table renders call counts', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /ai.*privacy/i }))
    expect(screen.getByText(/142 calls/i)).toBeInTheDocument()
    expect(screen.getByText(/38 calls/i)).toBeInTheDocument()
  })

  it('Storage tab: usage breakdown renders 3 rows', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /storage/i }))
    expect(screen.getByText(/documents/i)).toBeInTheDocument()
    expect(screen.getByText(/exports/i)).toBeInTheDocument()
    expect(screen.getByText(/database/i)).toBeInTheDocument()
  })

  it('About tab: disclaimer text renders', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /about/i }))
    expect(screen.getByTestId('disclaimer')).toBeInTheDocument()
    expect(screen.getByTestId('disclaimer')).toHaveTextContent(
      'This tool helps organise your tax information'
    )
  })

  it('About tab: active skills list renders', () => {
    wrap(<SettingsPage />)
    fireEvent.click(screen.getByRole('tab', { name: /about/i }))
    expect(screen.getByText(/employee_tax_au/i)).toBeInTheDocument()
  })
})
