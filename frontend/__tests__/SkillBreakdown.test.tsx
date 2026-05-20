import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SkillBreakdown from '@/components/readiness/SkillBreakdown'
import type { SkillBreakdownItem } from '@/lib/api/types'

const MOCK_BREAKDOWN: SkillBreakdownItem[] = [
  { skill_id: 'employee_tax_au', percentage: 80, achieved_weight: 4, total_weight: 5 },
  { skill_id: 'wfh_skill',       percentage: 60, achieved_weight: 3, total_weight: 5 },
]

describe('SkillBreakdown', () => {
  it('renders each skill row with display name and percentage', () => {
    render(<SkillBreakdown breakdown={MOCK_BREAKDOWN} />)
    expect(screen.getByText('Employee Tax')).toBeInTheDocument()
    expect(screen.getByText('Work From Home')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('60%')).toBeInTheDocument()
  })

  it('falls back to skill_id when display name is not mapped', () => {
    const breakdown: SkillBreakdownItem[] = [
      { skill_id: 'unknown_skill', percentage: 50, achieved_weight: 1, total_weight: 2 },
    ]
    render(<SkillBreakdown breakdown={breakdown} />)
    expect(screen.getByText('unknown_skill')).toBeInTheDocument()
  })

  it('renders no rows when breakdown is empty', () => {
    render(<SkillBreakdown breakdown={[]} />)
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument()
  })

  it('collapses and expands the list when toggle is clicked', async () => {
    const user = userEvent.setup()
    render(<SkillBreakdown breakdown={MOCK_BREAKDOWN} />)
    // Starts expanded — items visible
    expect(screen.getByText('Employee Tax')).toBeInTheDocument()
    // Click to collapse
    await user.click(screen.getByRole('button', { name: /per-skill breakdown/i }))
    expect(screen.queryByText('Employee Tax')).not.toBeInTheDocument()
    // Click to expand again
    await user.click(screen.getByRole('button', { name: /per-skill breakdown/i }))
    expect(screen.getByText('Employee Tax')).toBeInTheDocument()
  })
})
