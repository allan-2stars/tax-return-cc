import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const currencyQ: InterviewQuestion = {
  id: 'spouse_rfba_amount',
  ask: "What is your spouse's RFBA?",
  type: 'number',
  options: null,
  branches: null,
  required: false,
  why: null,
  hint: 'This appears on the PAYG Summary.',
  currency: true,
} as any

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const requiredCurrencyQ: InterviewQuestion = {
  ...currencyQ,
  required: true,
} as any

test('renders question text', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('Did you work from home?')).toBeInTheDocument()
})

test('renders all options as buttons with formatted labels', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByRole('button', { name: 'Yes Regular' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Yes Sometimes' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'No' })).toBeInTheDocument()
})

test('calls onAnswer with question id and raw option value', () => {
  const onAnswer = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={onAnswer} onBack={jest.fn()} onSkip={jest.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Yes Regular' }))
  expect(onAnswer).toHaveBeenCalledWith('wfh', 'yes_regular')
})

test('back button is visible by default and calls onBack', () => {
  const onBack = jest.fn()
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={onBack} onSkip={jest.fn()} />)
  const back = screen.getByRole('button', { name: /back/i })
  expect(back).toBeInTheDocument()
  fireEvent.click(back)
  expect(onBack).toHaveBeenCalled()
})

test('back button hidden when canGoBack is false', () => {
  render(
    <QuestionCard
      question={choiceQ}
      onAnswer={jest.fn()}
      onBack={jest.fn()}
      onSkip={jest.fn()}
      canGoBack={false}
    />
  )
  expect(screen.queryByRole('button', { name: /back/i })).not.toBeInTheDocument()
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
  expect(screen.getByRole('button', { name: 'Yes Regular' })).toBeDisabled()
  expect(screen.getByRole('button', { name: /skip/i })).toBeDisabled()
})

// ── New: info icon next to title ─────────────────────────────────────────────

test('info icon button shown when question.why exists', () => {
  render(<QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByRole('button', { name: /why do we ask/i })).toBeInTheDocument()
})

// ── New: numeric option guard ─────────────────────────────────────────────────

test('renders numeric option value without crashing', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const numQ: any = {
    id: 'pick_count',
    ask: 'How many?',
    type: 'single_choice',
    options: [1, 2, 3],  // numbers, not strings — as YAML might deliver them
    branches: null,
    required: false,
    why: null,
    hint: null,
  }
  expect(() =>
    render(<QuestionCard question={numQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  ).not.toThrow()
  expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument()
})

test('renders boolean-like options as Yes/No (not True/False) and preserves raw value', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const boolQ: any = {
    id: 'has_private_health',
    ask: 'Do you have private health insurance?',
    type: 'single_choice',
    options: [true, false],
    branches: null,
    required: false,
    why: null,
    hint: null,
  }
  const onAnswer = jest.fn()
  render(<QuestionCard question={boolQ} onAnswer={onAnswer} onBack={jest.fn()} onSkip={jest.fn()} />)

  // Display should be Yes/No (not True/False).
  expect(screen.getByRole('button', { name: 'Yes' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'No' })).toBeInTheDocument()

  // Raw value is preserved on submit (do not coerce to string).
  fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
  expect(onAnswer).toHaveBeenCalledWith('has_private_health', true)
})

// ── New: currency input ───────────────────────────────────────────────────────

test('currency input shows $ prefix', () => {
  render(<QuestionCard question={currencyQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('$')).toBeInTheDocument()
})

test('currency input hint shown below input', () => {
  render(<QuestionCard question={currencyQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByText('This appears on the PAYG Summary.')).toBeInTheDocument()
})

test('currency input skip button shown when not required', () => {
  render(<QuestionCard question={currencyQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument()
})

test('currency input shows custom error when submitted empty', async () => {
  const user = userEvent.setup()
  render(<QuestionCard question={requiredCurrencyQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /continue/i }))
  expect(await screen.findByRole('alert')).toBeInTheDocument()
})

// ── New: required text/number input validation ────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const requiredNumberQ: InterviewQuestion = {
  id: 'dependent_count',
  ask: 'How many dependent children do you have?',
  type: 'number',
  options: null,
  branches: null,
  required: true,
  why: null,
  hint: null,
}

test('required number input shows error when submitted empty', async () => {
  const user = userEvent.setup()
  render(<QuestionCard question={requiredNumberQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  await user.click(screen.getByRole('button', { name: /continue/i }))
  expect(await screen.findByRole('alert')).toBeInTheDocument()
})

test('dependent_count input includes min/max constraints', () => {
  const q: InterviewQuestion = {
    id: 'dependent_count',
    ask: 'How many dependent children do you have?',
    type: 'number',
    options: null,
    branches: null,
    required: false,
    why: null,
    hint: null,
  }
  render(<QuestionCard question={q} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  const input = screen.getByRole('spinbutton')
  expect(input).toHaveAttribute('min', '1')
  expect(input).toHaveAttribute('max', '20')
})

test('wfh_days input includes min/max constraints', () => {
  const q: InterviewQuestion = {
    id: 'wfh_days',
    ask: 'How many days per week did you regularly work from home?',
    type: 'number',
    options: null,
    branches: null,
    required: false,
    why: null,
    hint: null,
  }
  render(<QuestionCard question={q} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  const input = screen.getByRole('spinbutton')
  expect(input).toHaveAttribute('min', '1')
  expect(input).toHaveAttribute('max', '7')
})

test('spouse_rfba_amount currency input includes min/max constraints', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const q: any = {
    id: 'spouse_rfba_amount',
    ask: "What is your spouse's RFBA?",
    type: 'number',
    options: null,
    branches: null,
    required: false,
    why: null,
    hint: null,
    currency: true,
  }
  render(<QuestionCard question={q} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  const input = screen.getByRole('spinbutton')
  expect(input).toHaveAttribute('min', '0')
  expect(input).toHaveAttribute('max', '1000000')
})

test('numeric input is prefilled from currentAnswer', () => {
  const q: InterviewQuestion = {
    id: 'dependent_count',
    ask: 'How many dependent children do you have?',
    type: 'number',
    options: null,
    branches: null,
    required: false,
    why: null,
    hint: null,
  }
  render(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <QuestionCard question={q} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} {...({ currentAnswer: '3' } as any)} />
  )
  const input = screen.getByRole('spinbutton') as HTMLInputElement
  expect(input.value).toBe('3')
})

test('choice option matching currentAnswer is visually highlighted', () => {
  render(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} {...({ currentAnswer: 'yes_sometimes' } as any)} />
  )
  const selected = screen.getByRole('button', { name: 'Yes Sometimes' })
  expect(selected.className).toContain('border-accent')
})

test('serverError renders inline', () => {
  render(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <QuestionCard question={choiceQ} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} {...({ serverError: 'Value must be at least 1.' } as any)} />
  )
  expect(screen.getByText('Value must be at least 1.')).toBeInTheDocument()
})

test('form uses noValidate to suppress native browser popup', () => {
  const q: InterviewQuestion = {
    id: 'dependent_count',
    ask: 'How many dependent children do you have?',
    type: 'number',
    options: null,
    branches: null,
    required: false,
    why: null,
    hint: null,
  }
  render(<QuestionCard question={q} onAnswer={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />)
  const input = screen.getByRole('spinbutton')
  const form = input.closest('form')
  expect(form).toHaveAttribute('novalidate')
})
