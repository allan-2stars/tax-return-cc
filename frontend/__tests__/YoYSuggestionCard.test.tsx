import { render, screen, fireEvent } from '@testing-library/react'
import YoYSuggestionCard from '@/components/interview/YoYSuggestionCard'
import type { YoYSuggestion } from '@/lib/api/types'

const suggestion: YoYSuggestion = {
  id: 'sug-1',
  workspace_id: 'ws-123',
  source_workspace_id: null,
  financial_year: '2024-25',
  category: 'work_expense',
  description: 'Home internet (work portion)',
  amount_last_year: 180.00,
  frequency: 'annual',
  status: 'pending',
  actioned_at: null,
}

test('renders description', () => {
  render(<YoYSuggestionCard suggestion={suggestion} onAction={jest.fn()} />)
  expect(screen.getByText('Home internet (work portion)')).toBeInTheDocument()
})

test('renders three action buttons', () => {
  render(<YoYSuggestionCard suggestion={suggestion} onAction={jest.fn()} />)
  expect(screen.getByRole('button', { name: /yes, still use it/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /no longer/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /already added/i })).toBeInTheDocument()
})

test('calls onAction with "confirmed" on first button', () => {
  const onAction = jest.fn()
  render(<YoYSuggestionCard suggestion={suggestion} onAction={onAction} />)
  fireEvent.click(screen.getByRole('button', { name: /yes, still use it/i }))
  expect(onAction).toHaveBeenCalledWith('sug-1', 'confirmed')
})

test('calls onAction with "dismissed" on second button', () => {
  const onAction = jest.fn()
  render(<YoYSuggestionCard suggestion={suggestion} onAction={onAction} />)
  fireEvent.click(screen.getByRole('button', { name: /no longer/i }))
  expect(onAction).toHaveBeenCalledWith('sug-1', 'dismissed')
})

test('calls onAction with "not_applicable" on third button', () => {
  const onAction = jest.fn()
  render(<YoYSuggestionCard suggestion={suggestion} onAction={onAction} />)
  fireEvent.click(screen.getByRole('button', { name: /already added/i }))
  expect(onAction).toHaveBeenCalledWith('sug-1', 'not_applicable')
})
