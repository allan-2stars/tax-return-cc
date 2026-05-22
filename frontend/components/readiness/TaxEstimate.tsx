import type { TaxEstimateSummary } from '@/lib/api/types'

function fmt(value: string): string {
  const n = parseFloat(value)
  if (isNaN(n)) return value
  return `$${Math.round(n).toLocaleString('en-AU')}`
}

interface Props {
  data: TaxEstimateSummary | undefined
  isLoading: boolean
}

export default function TaxEstimate({ data, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-surface rounded-lg shadow-sm p-6 space-y-3 animate-pulse">
        <div className="h-4 bg-border rounded w-1/3" />
        <div className="h-3 bg-border rounded" />
        <div className="h-3 bg-border rounded w-3/4" />
      </div>
    )
  }

  if (!data) return null

  const rows = [
    { label: 'Gross income', value: fmt(data.gross_income) },
    { label: 'Total deductions', value: fmt(data.total_deductions) },
    { label: 'Taxable income', value: fmt(data.taxable_income) },
    { label: 'PAYG withheld', value: fmt(data.payg_withheld) },
  ]

  return (
    <div className="bg-surface rounded-lg shadow-sm p-6 space-y-4">
      <h2 className="font-display text-base font-semibold text-text-primary">
        Tax estimate
      </h2>

      <div className="space-y-2">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex justify-between items-baseline">
            <span className="text-sm font-ui text-text-body">{label}</span>
            <span className="text-sm font-mono text-text-primary">{value}</span>
          </div>
        ))}
      </div>

      {!data.confirmed_only && data.pending_count > 0 && (
        <p className="text-xs font-ui text-text-muted">
          {data.pending_count} item{data.pending_count !== 1 ? 's' : ''} still pending review — estimate will change.
        </p>
      )}

      <p className="text-xs font-ui text-text-muted">{data.disclaimer}</p>

      <a
        href={data.ato_calculator_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs font-ui text-accent underline"
      >
        ATO income tax calculator →
      </a>
    </div>
  )
}
