import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MissingEvidenceList from '@/components/readiness/MissingEvidenceList'
import type { MissingItem } from '@/lib/api/types'

const NOW_ITEMS: MissingItem[] = [
  { requirement_id: 'receipt', display: 'Work receipts', weight: 1.0, skill_id: 'employee_tax_au', how_to_get: 'Collect receipts from purchases' },
  { requirement_id: 'invoice', display: 'Tax invoices', weight: 0.5, skill_id: 'employee_tax_au' },
]

const AFTER_FY_ITEMS: MissingItem[] = [
  { requirement_id: 'payg', display: 'PAYG payment summary', weight: 2.0, skill_id: 'employee_tax_au', how_to_get: 'Download from myGov after July' },
]

describe('MissingEvidenceList', () => {
  it('renders "Available now" section with items', () => {
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.getByText('Available now')).toBeInTheDocument()
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
    expect(screen.getByText('Tax invoices')).toBeInTheDocument()
    expect(screen.getAllByText(/recommended/i).length).toBeGreaterThan(0)
  })

  it('renders "Available after FY" section with end date', () => {
    render(<MissingEvidenceList availableNow={[]} availableAfterFY={AFTER_FY_ITEMS} fyEndLabel="30 June 2025" />)
    expect(screen.getByText(/available after 30 june 2025/i)).toBeInTheDocument()
    expect(screen.getByText('PAYG payment summary')).toBeInTheDocument()
  })

  it('renders how_to_get hint when present', () => {
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.getByText('Collect receipts from purchases')).toBeInTheDocument()
  })

  it('does not render "Available after FY" section when list is empty', () => {
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.queryByText(/available after/i)).not.toBeInTheDocument()
  })

  it('uses stronger defer wording and required evidence warning copy', () => {
    render(<MissingEvidenceList availableNow={[]} availableAfterFY={AFTER_FY_ITEMS} fyEndLabel="30 June 2025" />)
    expect(screen.getByText(/i'll provide this later/i)).toBeInTheDocument()
    expect(
      screen.getByText(/required evidence left for later may keep readiness blocked and appear in export warnings/i)
    ).toBeInTheDocument()
    expect(screen.getByText(/usually required/i)).toBeInTheDocument()
  })

  it("hides an item after \"I'll provide this later\" is clicked", async () => {
    const user = userEvent.setup()
    render(<MissingEvidenceList availableNow={NOW_ITEMS} availableAfterFY={[]} fyEndLabel="30 June 2025" />)
    expect(screen.getByText('Work receipts')).toBeInTheDocument()
    const skipButtons = screen.getAllByRole('button', { name: /i'll provide this later/i })
    await user.click(skipButtons[0])
    expect(screen.queryByText('Work receipts')).not.toBeInTheDocument()
    // Other item still visible
    expect(screen.getByText('Tax invoices')).toBeInTheDocument()
  })
})
