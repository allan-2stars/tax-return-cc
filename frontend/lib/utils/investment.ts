export function daysBetween(d1: string, d2: string): number {
  const ms = Math.abs(new Date(d2).getTime() - new Date(d1).getTime())
  return Math.floor(ms / (1000 * 60 * 60 * 24))
}

export function cgtDiscountEligible(days: number): boolean {
  return days >= 365
}
