import { render, screen } from '@testing-library/react'
import StatusBadge from '@/components/shared/StatusBadge'

describe('StatusBadge', () => {
  it('confirmed → "Ready" with ready colour class', () => {
    render(<StatusBadge status="confirmed" />)
    const badge = screen.getByText('Ready')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-ready')
  })

  it('needs_user_review → "Needs your look" with review colour class', () => {
    render(<StatusBadge status="needs_user_review" />)
    const badge = screen.getByText('Needs your look')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-review')
  })

  it('needs_agent_review → "Agent review" with agent colour class', () => {
    render(<StatusBadge status="needs_agent_review" />)
    expect(screen.getByText('Agent review')).toHaveClass('text-agent')
  })

  it('high_risk → "Flag to review" with risk-high colour class', () => {
    render(<StatusBadge status="high_risk" />)
    expect(screen.getByText('Flag to review')).toHaveClass('text-risk-high')
  })

  it('out_of_scope → "Specialist area" with agent colour class', () => {
    render(<StatusBadge status="out_of_scope" />)
    expect(screen.getByText('Specialist area')).toHaveClass('text-agent')
  })

  it('missing → "Still needed" with muted colour class', () => {
    render(<StatusBadge status="missing" />)
    expect(screen.getByText('Still needed')).toHaveClass('text-text-muted')
  })

  it('duplicate → "Possible duplicate" with review colour class', () => {
    render(<StatusBadge status="duplicate" />)
    expect(screen.getByText('Possible duplicate')).toHaveClass('text-review')
  })
})
