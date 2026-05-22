import { render, screen, fireEvent } from '@testing-library/react'
import DeadlineBanner from '@/components/shared/DeadlineBanner'
import * as readinessHook from '@/lib/hooks/useReadiness'
import useWorkspaceStore from '@/lib/stores/workspace.store'

jest.mock('@/lib/hooks/useReadiness')
jest.mock('@/lib/stores/workspace.store')

const mockReadiness = readinessHook.useReadiness as jest.Mock
const mockStore = useWorkspaceStore as unknown as jest.Mock

function setStore(financialYear: string | null, userLodgerType: string | null = null) {
  mockStore.mockReturnValue({ financialYear, userLodgerType })
}

// Date freeze helpers
const OriginalDate = global.Date
function freezeDate(iso: string) {
  const frozen = new OriginalDate(iso)
  jest.spyOn(global, 'Date').mockImplementation((...args: unknown[]) => {
    if (args.length === 0) return frozen
    return new OriginalDate(...(args as ConstructorParameters<typeof Date>))
  }) as unknown
  ;(global.Date as unknown as { now: () => number }).now = () => frozen.getTime()
}
afterEach(() => {
  jest.restoreAllMocks()
  sessionStorage.clear()
})

beforeEach(() => {
  mockReadiness.mockReturnValue({ data: { percentage: 50 } })
  mockStore.mockReturnValue({ financialYear: '2024-25', userLodgerType: null })
})

describe('DeadlineBanner', () => {
  it('renders nothing when no financialYear', () => {
    setStore(null)
    const { container } = render(<DeadlineBanner />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when more than 30 days remain', () => {
    setStore('2024-25')
    freezeDate('2025-05-01T00:00:00.000Z') // ~60 days before June 30 2025
    const { container } = render(<DeadlineBanner />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders amber banner when 15 days remain', () => {
    setStore('2024-25')
    freezeDate('2025-06-15T00:00:00.000Z') // 15 days before June 30 2025
    render(<DeadlineBanner />)
    const alert = screen.getByRole('alert')
    expect(alert).toBeInTheDocument()
    expect(alert.className).toMatch(/review/)
  })

  it('renders terracotta banner when 5 days remain', () => {
    setStore('2024-25')
    freezeDate('2025-06-25T00:00:00.000Z') // 5 days before June 30 2025
    render(<DeadlineBanner />)
    const alert = screen.getByRole('alert')
    expect(alert.className).toMatch(/risk-high/)
  })

  it('dismisses when × is clicked and saves to sessionStorage', () => {
    setStore('2024-25')
    freezeDate('2025-06-25T00:00:00.000Z')
    render(<DeadlineBanner />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(sessionStorage.getItem('deadline-banner-dismissed')).toBe('1')
  })
})
