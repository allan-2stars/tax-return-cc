import { render, screen } from '@testing-library/react'
import NextStepsList from '@/components/interview/NextStepsList'

test('renders PAYG step for employee_tax_au skill', () => {
  render(<NextStepsList activatedSkills={['employee_tax_au']} />)
  expect(screen.getByText(/PAYG Payment Summary/i)).toBeInTheDocument()
})

test('renders crypto step only when crypto_skill_au is active', () => {
  render(<NextStepsList activatedSkills={['employee_tax_au']} />)
  expect(screen.queryByText(/crypto transaction history/i)).not.toBeInTheDocument()

  render(<NextStepsList activatedSkills={['employee_tax_au', 'crypto_skill_au']} />)
  expect(screen.getByText(/crypto transaction history/i)).toBeInTheDocument()
})

test('renders at most 3 steps when more than 3 skills are active', () => {
  render(<NextStepsList activatedSkills={['employee_tax_au', 'crypto_skill_au', 'wfh', 'investment_skill']} />)
  const links = screen.getAllByRole('link')
  expect(links.length).toBeLessThanOrEqual(3)
})

test('renders nothing when no known skills are active', () => {
  const { container } = render(<NextStepsList activatedSkills={['unknown_skill']} />)
  expect(container.firstChild).toBeNull()
})
