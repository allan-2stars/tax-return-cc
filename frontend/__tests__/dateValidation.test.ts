import { validateDate } from '@/lib/utils/fy'

describe('validateDate', () => {
  test('rejects non-ISO date strings', () => {
    expect(validateDate('18/12/2026', '2024-25').error).toMatch(/yyyy-mm-dd/i)
  })

  test('rejects unrealistic year 0001', () => {
    expect(validateDate('0001-01-01', '2024-25').error).toMatch(/1900/i)
  })

  test('accepts valid in-year dates', () => {
    expect(validateDate('2025-06-30', '2024-25').error).toBeUndefined()
  })
})
