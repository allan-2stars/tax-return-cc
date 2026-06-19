export function getFYEndLabel(fy: string): string {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return `30 June ${endYear}`
}

export function isFYActive(fy: string): boolean {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return new Date() < new Date(endYear, 5, 30)
}

export function computeNextFY(fy: string): string {
  const start = parseInt(fy.split('-')[0])
  const next = start + 1
  return `${next}-${String(next + 1).slice(-2)}`
}

export function daysUntilFYEnd(fy: string): number {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  const endDate = new Date(endYear, 5, 30) // June 30
  const now = new Date()
  return Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
}

export function deadlineState(fy: string): 'amber' | 'terracotta' | null {
  const days = daysUntilFYEnd(fy)
  if (days < 0) return null
  if (days <= 7) return 'terracotta'
  if (days <= 30) return 'amber'
  return null
}

const MIN_TAX_YEAR = 1900

function toIsoDateString(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function validateDate(
  value: string,
  financialYear: string | null,
): { error?: string; warning?: string } {
  if (!value) return {}

  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return { error: 'Enter a valid date in YYYY-MM-DD format.' }
  }

  const [yearText, monthText, dayText] = value.split('-')
  const year = parseInt(yearText, 10)
  const month = parseInt(monthText, 10)
  const day = parseInt(dayText, 10)

  if (year < MIN_TAX_YEAR) {
    return { error: `Year must be ${MIN_TAX_YEAR} or later.` }
  }

  const parsed = new Date(year, month - 1, day)
  if (
    Number.isNaN(parsed.getTime()) ||
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return { error: 'Enter a real calendar date.' }
  }

  const today = new Date()
  const todayStr = toIsoDateString(today)
  if (value > todayStr) {
    return { error: 'Date cannot be in the future.' }
  }

  if (!financialYear) return {}

  const fyStartYear = parseInt(financialYear.split('-')[0], 10)
  const fyEndYear = fyStartYear + 1
  const fyStartStr = `${fyStartYear}-07-01`
  const fyEndStr = `${fyEndYear}-06-30`

  if (value < fyStartStr || value > fyEndStr) {
    return {
      warning: `This date is outside FY ${financialYear} (1 Jul ${fyStartYear} – 30 Jun ${fyEndYear}). If this item belongs to a different year, consider adding it to that year's workspace.`,
    }
  }

  return {}
}
