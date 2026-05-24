import { daysBetween, cgtDiscountEligible } from '@/lib/utils/investment'

test('daysBetween returns 30 for Jan 1–31', () => {
  expect(daysBetween('2024-01-01', '2024-01-31')).toBe(30)
})

test('daysBetween is order-independent', () => {
  expect(daysBetween('2024-01-31', '2024-01-01')).toBe(30)
})

test('cgtDiscountEligible: true for exactly 365 days', () => {
  expect(cgtDiscountEligible(365)).toBe(true)
})

test('cgtDiscountEligible: true for > 365 days', () => {
  expect(cgtDiscountEligible(400)).toBe(true)
})

test('cgtDiscountEligible: false for 364 days', () => {
  expect(cgtDiscountEligible(364)).toBe(false)
})
