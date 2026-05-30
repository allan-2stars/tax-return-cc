import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

const mockGetSession = interviewApi.getSession as jest.Mock
const mockGetYoySuggestions = interviewApi.getYoySuggestions as jest.Mock
const mockRestartInterview = interviewApi.restartInterview as jest.Mock
const mockGoBack = interviewApi.goBack as jest.Mock
const mockCancelEdit = interviewApi.cancelEdit as jest.Mock
const mockUseInterviewStore = useInterviewStore as jest.Mock
const mockSetNewSkillPending = jest.fn()
let invalidateSpy: jest.SpyInstance

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const SESSION = (state: string, question?: object, extra?: object) => ({
  data: {
    data: {
      state,
      current_question: question ?? null,
      activated_skills: ['employee_tax_au'],
      progress: { completed: 1, total: 5 },
      ...(extra ?? {}),
    },
  },
})

const QUESTION = {
  id: 'wfh', ask: 'Did you work from home?', type: 'single_choice',
  options: ['yes', 'no'], branches: null, required: false, why: null, hint: null,
}

beforeEach(() => {
  jest.clearAllMocks()
  invalidateSpy = jest.spyOn(QueryClient.prototype, 'invalidateQueries')
  mockUseInterviewStore.mockReturnValue({
    newSkillPending: null,
    setNewSkillPending: mockSetNewSkillPending,
  })
  mockGetYoySuggestions.mockResolvedValue({ data: { data: [] } })
})

afterEach(() => {
  invalidateSpy.mockRestore()
})

test('shows loading state initially', () => {
  mockGetSession.mockReturnValue(new Promise(() => {}))
  wrap(<JourneyPage />)
  expect(screen.getByText(/loading/i)).toBeInTheDocument()
})

test('shows start CTA when state is not_started', async () => {
  mockGetSession.mockResolvedValue(SESSION('not_started'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument())
})

test('shows QuestionCard when state is in_progress', async () => {
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
})

test('back in normal flow uses goBack and does not cancel edit', async () => {
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION, {
    edit_mode: false,
  }))
  mockGoBack.mockResolvedValue({
    data: { data: {
      session_id: 'abc',
      state: 'in_progress',
      current_question: {
        id: 'lodger_type',
        ask: 'How are you planning to lodge your return?',
        type: 'single_choice',
        options: ['self', 'agent'],
        branches: null,
        required: false,
        why: null,
        hint: null,
      },
      progress: { completed: 0, total: 5 },
      edit_mode: false,
      edit_target: null,
      edit_flow_completed: 0,
      edit_flow_total: 0,
    } },
  })

  const user = userEvent.setup()
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: /back/i }))

  await waitFor(() => expect(mockGoBack).toHaveBeenCalled())
  expect(mockCancelEdit).not.toHaveBeenCalled()
})

test('back in edit mode cancels edit and returns to summary instead of normal back', async () => {
  mockGetSession
    .mockResolvedValueOnce(SESSION('in_progress', QUESTION, {
      edit_mode: true,
      edit_target: 'wfh',
      edit_flow_completed: 0,
      edit_flow_total: 1,
    }))
    .mockResolvedValue(SESSION('awaiting_evidence'))
  mockCancelEdit.mockResolvedValue({
    data: { data: {
      state: 'awaiting_evidence',
      current_question: null,
      activated_skills: ['employee_tax_au'],
      progress: { completed: 5, total: 5 },
      edit_mode: false,
      edit_target: null,
      edit_flow_completed: 0,
      edit_flow_total: 0,
    } },
  })

  const user = userEvent.setup()
  wrap(<JourneyPage />)

  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: /back/i }))

  await waitFor(() => expect(mockCancelEdit).toHaveBeenCalled())
  expect(mockGoBack).not.toHaveBeenCalled()
  await waitFor(() => expect(screen.getByText(/you're all set up/i)).toBeInTheDocument())
})

test('back in edit mode traverses mini-flow via normal back when not at edit root', async () => {
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION, {
    edit_mode: true,
    edit_target: 'wfh',
    edit_flow_completed: 1,
    edit_flow_total: 2,
  }))
  mockGoBack.mockResolvedValue({
    data: { data: {
      session_id: 'abc',
      state: 'in_progress',
      current_question: {
        id: 'wfh_method',
        ask: 'Which WFH calculation method are you using?',
        type: 'single_choice',
        options: ['fixed_rate', 'actual_cost'],
        branches: null,
        required: false,
        why: null,
        hint: null,
      },
      progress: { completed: 4, total: 6 },
      edit_mode: true,
      edit_target: 'wfh',
      edit_flow_completed: 0,
      edit_flow_total: 1,
    } },
  })

  const user = userEvent.setup()
  wrap(<JourneyPage />)

  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: /back/i }))

  await waitFor(() => expect(mockGoBack).toHaveBeenCalled())
  expect(mockCancelEdit).not.toHaveBeenCalled()
})

test('progress dots use edit mini-flow total when editing one question', async () => {
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION, {
    edit_mode: true,
    edit_target: 'wfh',
    edit_flow_completed: 0,
    edit_flow_total: 1,
  }))

  wrap(<JourneyPage />)

  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
  expect(screen.getAllByTestId('dot')).toHaveLength(1)
  expect(screen.getByLabelText('0 of 1 questions answered')).toBeInTheDocument()
})

test('shows completion screen when state is awaiting_evidence', async () => {
  mockGetSession.mockResolvedValue(SESSION('awaiting_evidence'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/you're all set up/i)).toBeInTheDocument())
})

test('in-progress with no current question but incomplete questions renders safe summary state', async () => {
  mockGetSession.mockResolvedValue({
    data: {
      data: {
        state: 'in_progress',
        current_question: null,
        activated_skills: ['employee_tax_au'],
        progress: { completed: 1, total: 5 },
        incomplete_questions: [
          { question_id: 'fy_confirm', question_label: 'Financial year', editable: true },
        ],
      },
    },
  })
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/some questions still need answers/i)).toBeInTheDocument())
})

test('shows restart journey screen when needs_restart is true', async () => {
  mockGetSession
    .mockResolvedValueOnce(SESSION('awaiting_evidence', undefined, { needs_restart: true }))
    .mockResolvedValueOnce(SESSION('in_progress', QUESTION))
  mockRestartInterview.mockResolvedValue({ data: { data: {} } })

  const user = userEvent.setup()
  wrap(<JourneyPage />)

  await waitFor(() => expect(screen.getByText(/needs attention/i)).toBeInTheDocument())
  expect(screen.queryByText(/you're all set up/i)).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: /restart tax journey/i }))
  await waitFor(() => expect(mockRestartInterview).toHaveBeenCalled())
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
})

test('renders completion screen when state is complete', async () => {
  mockGetSession.mockResolvedValue(SESSION('complete'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByRole('button', { name: /tax readiness/i })).toBeInTheDocument())
})

test('shows error state on API failure', async () => {
  mockGetSession.mockRejectedValue(new Error('Network error'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/unable to load/i)).toBeInTheDocument())
})

test('new skill banner renders when newSkillPending is set', async () => {
  mockUseInterviewStore.mockReturnValue({
    newSkillPending: 'wfh_skill',
    setNewSkillPending: mockSetNewSkillPending,
  })
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/we found something new/i)).toBeInTheDocument())
})

test('shows personalised next step for active skill on awaiting_evidence', async () => {
  mockGetSession.mockResolvedValue(SESSION('awaiting_evidence'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/PAYG Payment Summary/i)).toBeInTheDocument())
})

test('returns to completion screen immediately when answer response state is awaiting_evidence (edit mode)', async () => {
  const mockAnswerQuestion = interviewApi.answerQuestion as jest.Mock
  const mockCompleteInterview = interviewApi.completeInterview as jest.Mock
  const mockInvalidateQueries = jest.fn()

  mockGetSession
    .mockResolvedValueOnce(SESSION('in_progress', QUESTION))
    .mockResolvedValue(SESSION('awaiting_evidence'))
  mockAnswerQuestion.mockResolvedValue({
    data: { data: {
      state: 'awaiting_evidence',
      next_question: null,
      activated_skills: ['employee_tax_au'],
      progress: { completed: 5, total: 5 },
    } },
  })

  const user = userEvent.setup()
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())

  await user.click(screen.getByRole('button', { name: 'Yes' }))

  // completeInterview must NOT be called — session is already awaiting_evidence
  await waitFor(() => expect(screen.getByText(/you're all set up/i)).toBeInTheDocument())
  expect(mockCompleteInterview).not.toHaveBeenCalled()
})

test('calls completeInterview and shows completion screen when last answer exhausts queue', async () => {
  const mockAnswerQuestion = interviewApi.answerQuestion as jest.Mock
  const mockCompleteInterview = interviewApi.completeInterview as jest.Mock

  mockGetSession
    .mockResolvedValueOnce(SESSION('in_progress', QUESTION))
    .mockResolvedValue(SESSION('awaiting_evidence'))
  mockAnswerQuestion.mockResolvedValue({
    data: { data: {
      state: 'in_progress',
      next_question: null,
      activated_skills: ['employee_tax_au'],
      progress: { completed: 5, total: 5 },
    } },
  })
  mockCompleteInterview.mockResolvedValue({
    data: { data: { session_id: 'abc', state: 'awaiting_evidence' } },
  })

  const user = userEvent.setup()
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())

  await user.click(screen.getByRole('button', { name: 'Yes' }))

  await waitFor(() => expect(mockCompleteInterview).toHaveBeenCalled())
  await waitFor(() => expect(screen.getByText(/you're all set up/i)).toBeInTheDocument())
})

test('skip invalidates session/summary/readiness/export eligibility caches', async () => {
  const mockSkipQuestion = interviewApi.skipQuestion as jest.Mock
  mockGetSession.mockResolvedValue(SESSION('in_progress', QUESTION))
  mockSkipQuestion.mockResolvedValue({
    data: { data: {
      state: 'in_progress',
      next_question: {
        id: 'lodger_type',
        ask: 'How are you planning to lodge your return?',
        type: 'single_choice',
        options: ['self', 'agent'],
        branches: null,
        required: false,
        why: null,
        hint: null,
      },
      progress: { completed: 2, total: 5 },
    } },
  })

  const user = userEvent.setup()
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText('Did you work from home?')).toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: /skip for now/i }))

  await waitFor(() => expect(mockSkipQuestion).toHaveBeenCalled())
  await waitFor(() => {
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['interview', 'session'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['interview', 'summary'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['readiness'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['export-eligibility'] })
  })
})
