import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import JourneyPage from '@/app/(dashboard)/journey/page'
import * as interviewApi from '@/lib/api/interview'
import useInterviewStore from '@/lib/stores/interview.store'

jest.mock('@/lib/api/interview')
jest.mock('@/lib/stores/interview.store', () => ({
  __esModule: true,
  default: jest.fn(),
}))
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}))
jest.mock('@/components/interview/QuestionCard', () => ({
  __esModule: true,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  default: (props: any) => (
    <div>
      <div>{props.question.ask}</div>
      <div data-testid="qc-current-answer">{String(props.currentAnswer ?? '')}</div>
      {props.serverError && <div data-testid="qc-server-error">{props.serverError}</div>}
      <button type="button" onClick={() => props.onAnswer(props.question.id, '1')}>
        SubmitAnswer
      </button>
      <button type="button" onClick={() => props.onSkip(props.question.id)}>
        SkipNow
      </button>
    </div>
  ),
}))

const mockGetSession = interviewApi.getSession as jest.Mock
const mockAnswerQuestion = interviewApi.answerQuestion as jest.Mock
const mockSkipQuestion = interviewApi.skipQuestion as jest.Mock
const mockGetYoySuggestions = interviewApi.getYoySuggestions as jest.Mock
const mockUseInterviewStore = useInterviewStore as jest.Mock

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const Q1 = {
  id: 'dependent_count',
  ask: 'How many dependent children do you have?',
  type: 'number',
  options: null,
  branches: null,
  required: false,
  why: null,
  hint: null,
}

const Q2 = {
  id: 'lodger_type',
  ask: 'How are you planning to lodge your return?',
  type: 'single_choice',
  options: ['self', 'agent'],
  branches: null,
  required: false,
  why: null,
  hint: null,
}

const SESSION = (question: object) => ({
  data: {
    data: {
      state: 'in_progress',
      current_question: question,
      answers: { dependent_count: '3' },
      activated_skills: ['employee_tax_au'],
      progress: { completed: 1, total: 5 },
    },
  },
})

beforeEach(() => {
  jest.clearAllMocks()
  mockUseInterviewStore.mockReturnValue({
    newSkillPending: null,
    setNewSkillPending: jest.fn(),
  })
  mockGetYoySuggestions.mockResolvedValue({ data: { data: [] } })
})

test('passes answers[current_question.id] to QuestionCard as currentAnswer', async () => {
  mockGetSession.mockResolvedValue(SESSION(Q1))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(Q1.ask)).toBeInTheDocument())
  expect(screen.getByTestId('qc-current-answer')).toHaveTextContent('3')
})

test('backend 422 detail.message is shown inline as serverError', async () => {
  mockGetSession.mockResolvedValue(SESSION(Q1))
  mockAnswerQuestion.mockRejectedValue({
    response: {
      status: 422,
      data: { detail: { message: 'wfh_days must be between 1 and 7' } },
    },
  })
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(Q1.ask)).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: 'SubmitAnswer' }))
  await waitFor(() =>
    expect(screen.getByTestId('qc-server-error')).toHaveTextContent('wfh_days must be between 1 and 7')
  )
})

test('serverError clears after successful answer', async () => {
  mockGetSession.mockResolvedValue(SESSION(Q1))
  mockAnswerQuestion
    .mockRejectedValueOnce({
      response: {
        status: 422,
        data: { detail: { message: 'dependent_count must be between 1 and 20' } },
      },
    })
    .mockResolvedValueOnce({
      data: {
        data: {
          state: 'in_progress',
          next_question: Q2,
          activated_skills: ['employee_tax_au'],
          progress: { completed: 2, total: 5 },
        },
      },
    })

  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(Q1.ask)).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: 'SubmitAnswer' }))
  await waitFor(() =>
    expect(screen.getByTestId('qc-server-error')).toHaveTextContent('dependent_count must be between 1 and 20')
  )

  fireEvent.click(screen.getByRole('button', { name: 'SubmitAnswer' }))
  await waitFor(() => expect(screen.getByText(Q2.ask)).toBeInTheDocument())
  expect(screen.queryByTestId('qc-server-error')).not.toBeInTheDocument()
})

test('serverError clears when question changes', async () => {
  mockGetSession.mockResolvedValue(SESSION(Q1))
  mockAnswerQuestion.mockRejectedValue({
    response: {
      status: 422,
      data: { detail: { message: 'dependent_count must be between 1 and 20' } },
    },
  })
  mockSkipQuestion.mockResolvedValue({
    data: {
      data: {
        state: 'in_progress',
        next_question: Q2,
        progress: { completed: 2, total: 5 },
      },
    },
  })

  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(Q1.ask)).toBeInTheDocument())

  fireEvent.click(screen.getByRole('button', { name: 'SubmitAnswer' }))
  await waitFor(() =>
    expect(screen.getByTestId('qc-server-error')).toHaveTextContent('dependent_count must be between 1 and 20')
  )

  fireEvent.click(screen.getByRole('button', { name: 'SkipNow' }))
  await waitFor(() => expect(screen.getByText(Q2.ask)).toBeInTheDocument())
  expect(screen.queryByTestId('qc-server-error')).not.toBeInTheDocument()
})
