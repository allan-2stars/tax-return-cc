export function getFYEndLabel(fy: string): string {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return `30 June ${endYear}`
}

export function isFYActive(fy: string): boolean {
  const endYear = parseInt(fy.split('-')[1]) + 2000
  return new Date() < new Date(endYear, 5, 30)
}
