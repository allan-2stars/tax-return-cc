import { render, screen } from '@testing-library/react'
import TaxEstimate from '@/components/readiness/TaxEstimate'
import type { TaxEstimateSummary } from '@/lib/api/types'

const mockData: TaxEstimateSummary = {
  gross_income: '85000.00',
  total_deductions: '3200.00',
  taxable_income: '81800.00',
  payg_withheld: '20000.00',
  confirmed_only: false,
  pending_count: 5,
  ato_calculator_url: 'https://www.ato.gov.au/calculators',
  disclaimer: 'Indicative estimate only.',
}

describe('TaxEstimate', () => {
  it('renders gross income', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    expect(screen.getByText(/gross income/i)).toBeInTheDocument()
    expect(screen.getByText('$85,000')).toBeInTheDocument()
  })

  it('renders taxable income and deductions', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    expect(screen.getByText(/total deductions/i)).toBeInTheDocument()
    expect(screen.getByText('$3,200')).toBeInTheDocument()
    expect(screen.getByText(/taxable income/i)).toBeInTheDocument()
    expect(screen.getByText('$81,800')).toBeInTheDocument()
  })

  it('renders pending items notice when pending_count > 0', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    expect(screen.getByText(/5 items? still/i)).toBeInTheDocument()
  })

  it('renders ATO calculator link', () => {
    render(<TaxEstimate data={mockData} isLoading={false} />)
    const link = screen.getByRole('link', { name: /ato/i })
    expect(link).toHaveAttribute('href', 'https://www.ato.gov.au/calculators')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
