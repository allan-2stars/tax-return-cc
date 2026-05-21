import { render, screen, fireEvent } from '@testing-library/react'
import QuestionCard from '@/components/interview/QuestionCard'
import type { InterviewQuestion } from '@/lib/api/types'

const choiceQ: InterviewQuestion = {
  id: 'wfh',
  ask: 'Did you work from home?',
  type: 'single_choice',
  options: ['yes_regular', 'yes_sometimes', 'no'],
  branches: null,
  required: false,
  why: 'This helps determine your WFH deduction eligibility.',
  hint: null,
}

const requiredQ: InterviewQuestion = {
  id: 'residency',
  ask: 'What is your residency status?',
  type: 'single_choice',
  options: ['resident', 'non_resident'],
  branches: null,
  required: true,
  why: null,
  hint: 'For most Australians, this is "resident".',
}

test('renders question text', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('Did you work from home?')).toBeInTheDocument()
})

test('renders all options as buttons', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByRole('button', { name: 'yes_regular' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'yes_sometimes' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'no' })).toBeInTheDocument()
})

test('calls onAnswer with question id and selected option', () => {
  const onAnswer = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={onAnswer} onBack={jest.fn()} onSkip={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'yes_regular' }))
  expect(onAnswer).toHaveBeenCalledWith('wfh', 'yes_regular')
})

test('back button is always visible and calls onBack', () => {
  const onBack = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={onBack} onSkip={jest.fn()} />)
  const back = screen.getByRole('button', { name: /back/i })
  expect(back).toBeInTheDocument()
  fireEvent.click(back)
  expect(onBack).toHaveBeenCalled()
})

test('skip button shown and calls onSkip for non-required questions', () => {
  const onSkip = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={onSkip} />)
  const skipBtn = screen.getByRole('button', { name: /skip/i })
  expect(skipBtn).toBeInTheDocument()
  fireEvent.click(skipBtn)
  expect(onSkip).toHaveBeenCalledWith('wfh')
})

test('skip button hidden for required questions', () => {
  render(<QuestionCard question={requiredQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.queryByRole('button', { name: /skip/i })).not.toBeInTheDocument()
})

test('hint text shown when present', () => {
  render(<QuestionCard question={requiredQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('For most Australians, this is "resident".')).toBeInTheDocument()
})

test('why tooltip hidden initially, shown on toggle', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.queryByText('This helps determine your WFH deduction eligibility.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /why do we ask/i }))
  expect(screen.getByText('This helps determine your WFH deduction eligibility.')).toBeInTheDocument()
})

test('why button absent when question.why is null', () => {
  render(<QuestionCard question={requiredQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.queryByRole('button', { name: /why do we ask/i })).not.toBeInTheDocument()
})

test('all interactive buttons disabled when isSubmitting', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} isSubmitting />)
  expect(screen.getByRole('button', { name: /back/i })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'yes_regular' })).toBeDisabled()
  expect(screen.getByRole('button', { name: /skip/i })).toBeDisabled()
})
