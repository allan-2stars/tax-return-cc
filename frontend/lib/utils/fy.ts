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
