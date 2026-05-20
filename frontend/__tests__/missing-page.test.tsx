import { render, screen } from '@testing-library/react'
import MissingPage from '@/app/(dashboard)/readiness/missing/page'

jest.mock('@/lib/hooks/useReadiness', () => ({
  useMissing: jest.fn(),
  __esModule: true,
}))

jest.mock('@/lib/stores/workspace.store', () => ({
  default: () => ({
    workspaceId: 'ws-1',
    financialYear: '2024-25',
  }),
  __esModule: true,
}))

import { useMissing as mockUseMissing } from '@/lib/hooks/useReadiness'

const MOCK_MISSING = {
  available_now: [
    { requirement_id: 'receipt', display: 'Work receipts', weight: 1.0, skill_id: 'employee_tax_au', how_to_get: 'Keep your receipts' },
  ],
  available_after_fy: [
    { requirement_id: 'payg', display: 'PAYG payment summary', weight: 2.0, skill_id: 'employee_tax_au', how_to_get: 'Download from myGov' },
  ],
}

beforeEach(() => jest.clearAllMocks())

describe('MissingPage', () => {
  it('shows loading state while data is fetching', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: true, data: undefined })
    render(<MissingPage />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows page heading', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    render(<MissingPage />)
    expect(screen.getByRole('heading', { name: /missing evidence/i })).toBeInTheDocument()
  })

  it('renders available now items', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    render(<MissingPage />)
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
  })

  it('renders available after FY items', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({ isLoading: false, data: MOCK_MISSING })
    render(<MissingPage />)
    expect(screen.getByText('PAYG payment summary')).toBeInTheDocument()
  })

  it('shows empty state when both lists are empty', () => {
    ;(mockUseMissing as jest.Mock).mockReturnValue({
      isLoading: false,
      data: { available_now: [], available_after_fy: [] },
    })
    render(<MissingPage />)
    expect(screen.getByText(/nothing missing/i)).toBeInTheDocument()
  })
})
