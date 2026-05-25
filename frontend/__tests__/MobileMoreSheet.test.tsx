import { render, screen, fireEvent } from '@testing-library/react'
import MobileMoreSheet from '@/components/shared/MobileMoreSheet'
import { Package, Settings } from 'lucide-react'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/',
}))

const mockItems = [
  { href: '/export', label: 'Export Review Pack', icon: Package },
  { href: '/settings', label: 'Settings', icon: Settings },
]

describe('MobileMoreSheet', () => {
  it('contains Export and Settings links', () => {
    render(<MobileMoreSheet onClose={jest.fn()} items={mockItems} />)
    expect(screen.getByRole('link', { name: /export review pack/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /settings/i })).toBeInTheDocument()
  })

  it('calls onClose when backdrop is clicked', () => {
    const onClose = jest.fn()
    render(<MobileMoreSheet onClose={onClose} items={mockItems} />)
    fireEvent.click(screen.getByTestId('more-sheet-backdrop'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when a nav link is clicked', () => {
    const onClose = jest.fn()
    render(<MobileMoreSheet onClose={onClose} items={mockItems} />)
    fireEvent.click(screen.getByRole('link', { name: /settings/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
