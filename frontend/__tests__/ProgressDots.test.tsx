import { render, screen } from '@testing-library/react'
import ProgressDots from '@/components/interview/ProgressDots'

test('renders correct total number of dots', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  expect(container.querySelectorAll('[data-testid="dot"]')).toHaveLength(5)
})

test('completed dots have bg-ready class', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  const dots = container.querySelectorAll('[data-testid="dot"]')
  expect(dots[0].className).toContain('bg-ready')
  expect(dots[1].className).toContain('bg-ready')
})

test('current dot (index = completed) has bg-accent class', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  const dots = container.querySelectorAll('[data-testid="dot"]')
  expect(dots[2].className).toContain('bg-accent')
})

test('upcoming dots have bg-border class', () => {
  const { container } = render(<ProgressDots completed={2} total={5} />)
  const dots = container.querySelectorAll('[data-testid="dot"]')
  expect(dots[3].className).toContain('bg-border')
  expect(dots[4].className).toContain('bg-border')
})

test('has accessible aria-label', () => {
  render(<ProgressDots completed={2} total={5} />)
  expect(screen.getByLabelText('2 of 5 questions answered')).toBeInTheDocument()
})

test('clamps invalid completed and total values', () => {
  const { container } = render(<ProgressDots completed={-3} total={0} />)
  expect(container.querySelectorAll('[data-testid="dot"]')).toHaveLength(1)
  expect(screen.getByLabelText('0 of 1 questions answered')).toBeInTheDocument()
})

test('caps rendered dots at a safe maximum', () => {
  const { container } = render(<ProgressDots completed={12} total={200} />)
  expect(container.querySelectorAll('[data-testid="dot"]')).toHaveLength(12)
})
