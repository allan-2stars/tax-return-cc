import { render, screen } from '@testing-library/react'
import ConfidenceBar from '@/components/shared/ConfidenceBar'

describe('ConfidenceBar', () => {
  it('0.95 → "High confidence"', () => {
    render(<ConfidenceBar confidence={0.95} />)
    expect(screen.getByText('High confidence')).toBeInTheDocument()
  })

  it('0.90 → "High confidence" (boundary)', () => {
    render(<ConfidenceBar confidence={0.90} />)
    expect(screen.getByText('High confidence')).toBeInTheDocument()
  })

  it('0.80 → "Moderate"', () => {
    render(<ConfidenceBar confidence={0.80} />)
    expect(screen.getByText('Moderate')).toBeInTheDocument()
  })

  it('0.70 → "Moderate" (boundary)', () => {
    render(<ConfidenceBar confidence={0.70} />)
    expect(screen.getByText('Moderate')).toBeInTheDocument()
  })

  it('0.60 → "Uncertain"', () => {
    render(<ConfidenceBar confidence={0.60} />)
    expect(screen.getByText('Uncertain')).toBeInTheDocument()
  })

  it('0.30 → "Needs review"', () => {
    render(<ConfidenceBar confidence={0.30} />)
    expect(screen.getByText('Needs review')).toBeInTheDocument()
  })

  it('bar fill has bg-ready class for high confidence', () => {
    const { container } = render(<ConfidenceBar confidence={0.95} />)
    const bar = container.querySelector('[data-testid="confidence-fill"]')
    expect(bar).toHaveClass('bg-ready')
  })

  it('bar fill has bg-agent class for low confidence', () => {
    const { container } = render(<ConfidenceBar confidence={0.30} />)
    const bar = container.querySelector('[data-testid="confidence-fill"]')
    expect(bar).toHaveClass('bg-agent')
  })
})
