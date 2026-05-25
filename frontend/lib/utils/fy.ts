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

export function validateDate(
  value: string,
  financialYear: string | null,
): { error?: string; warning?: string } {
  if (!value) return {}

  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  if (value > todayStr) {
    return { error: 'Date cannot be in the future' }
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
