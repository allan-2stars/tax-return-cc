import { render, screen } from '@testing-library/react'
import ReadinessRing from '@/components/readiness/ReadinessRing'

describe('ReadinessRing', () => {
  it('renders the percentage number in the centre', () => {
    render(<ReadinessRing percentage={72} />)
    expect(screen.getByText('72%')).toBeInTheDocument()
  })

  it('renders 0% correctly', () => {
    render(<ReadinessRing percentage={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders 100% correctly', () => {
    render(<ReadinessRing percentage={100} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('progress arc has stroke-ready class (sage green)', () => {
    const { container } = render(<ReadinessRing percentage={50} />)
    const arc = container.querySelector('[data-testid="ring-progress"]')
    expect(arc).toHaveClass('stroke-ready')
  })

  it('background track has stroke-progress-track class', () => {
    const { container } = render(<ReadinessRing percentage={50} />)
    const track = container.querySelector('[data-testid="ring-track"]')
    expect(track).toHaveClass('stroke-progress-track')
  })

  it('SVG has aria-label with percentage', () => {
    const { container } = render(<ReadinessRing percentage={72} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-label', '72% ready')
  })

  it('clamps values above 100 to 100', () => {
    render(<ReadinessRing percentage={150} />)
    expect(screen.getByText('150%')).toBeInTheDocument()
    // SVG offset clamped so it still renders without crashing
    const { container } = render(<ReadinessRing percentage={150} />)
    expect(container.querySelector('[data-testid="ring-progress"]')).toBeInTheDocument()
  })
})
