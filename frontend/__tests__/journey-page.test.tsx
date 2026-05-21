import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import JourneyPage from '@/app/(dashboard)/journey/page'
import * as interviewApi from '@/lib/api/interview'
import useInterviewStore from '@/lib/stores/interview.store'

jest.mock('@/lib/api/interview')
jest.mock('@/lib/stores/interview.store', () => ({
  __esModule: true,
  default: jest.fn(),
}))

const mockGetSession = interviewApi.getSession as jest.Mock
const mockGetYoySuggestions = interviewApi.getYoySuggestions as jest.Mock
const mockUseInterviewStore = useInterviewStore as jest.Mock
const mockSetNewSkillPending = jest.fn()

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const SESSION = (state: string, question?: object) => ({
  data: {
    data: {
      state,
      current_question: question ?? null,
      activated_skills: ['employee_tax_au'],
      progress: { completed: 1, total: 5 },
    },
  },
})

const QUESTION = {
  id: 'wfh', ask: 'Did you work from home?', type: 'single_choice',
  options: ['yes', 'no'], branches: null, required: false, why: null, hint: null,
}

beforeEach(() => {
  jest.clearAllMocks()
  mockUseInterviewStore.mockReturnValue({
    newSkillPending: null,
    setNewSkillPending: mockSetNewSkillPending,
  })
  mockGetYoySuggestions.mockResolvedValue({ data: { data: [] } })
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

test('shows completion screen when state is awaiting_evidence', async () => {
  mockGetSession.mockResolvedValue(SESSION('awaiting_evidence'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByText(/you're all set up/i)).toBeInTheDocument())
})

test('shows link to readiness when state is complete', async () => {
  mockGetSession.mockResolvedValue(SESSION('complete'))
  wrap(<JourneyPage />)
  await waitFor(() => expect(screen.getByRole('link', { name: /readiness/i })).toBeInTheDocument())
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
