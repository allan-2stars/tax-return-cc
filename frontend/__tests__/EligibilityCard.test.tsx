import { render, screen, fireEvent } from '@testing-library/react'
import EligibilityCard from '@/components/export/EligibilityCard'
import type { ExportEligibility } from '@/lib/api/types'

const blocked: ExportEligibility = {
  can_export: false,
  blocking_reasons: ['Interview must be complete before exporting. Please finish the interview first.'],
  warnings: [],
}

const warnOnly: ExportEligibility = {
  can_export: true,
  blocking_reasons: [],
  warnings: ['3 review item(s) have not been confirmed. Consider reviewing them before exporting.'],
}

describe('EligibilityCard', () => {
  it('renders blocked state — shows reason, hides Generate anyway', () => {
    render(<EligibilityCard eligibility={blocked} onGenerateAnyway={jest.fn()} />)
    expect(screen.getByText(/cannot export/i)).toBeInTheDocument()
    expect(screen.getByText(/interview must be complete/i)).toBeInTheDocument()
    expect(screen.queryByText(/generate anyway/i)).not.toBeInTheDocument()
  })

  it('renders ready state — shows ready message, no Generate anyway', () => {
    const ready: ExportEligibility = { can_export: true, blocking_reasons: [], warnings: [] }
    render(<EligibilityCard eligibility={ready} onGenerateAnyway={jest.fn()} />)
    expect(screen.getByText(/ready to export/i)).toBeInTheDocument()
    expect(screen.queryByText(/generate anyway/i)).not.toBeInTheDocument()
  })

  it('renders warning state — shows warning, shows Generate anyway, calls callback', () => {
    const onGenerateAnyway = jest.fn()
    render(<EligibilityCard eligibility={warnOnly} onGenerateAnyway={onGenerateAnyway} />)
    expect(screen.getByText(/3 review item/i)).toBeInTheDocument()
    const btn = screen.getByText(/generate anyway/i)
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    expect(onGenerateAnyway).toHaveBeenCalledTimes(1)
  })
})
