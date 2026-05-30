import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import InterviewSummary from '@/components/interview/InterviewSummary'
import * as interviewApi from '@/lib/api/interview'

jest.mock('@/lib/api/interview')

const mockGetInterviewSummary = interviewApi.getInterviewSummary as jest.Mock
const mockJumpToQuestion = interviewApi.jumpToQuestion as jest.Mock
let invalidateSpy: jest.SpyInstance

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const SUMMARY_DATA = {
  sections: [
    {
      title: 'Your situation',
      answers: [
        {
          question_id: 'residency',
          question_label: 'Residency status',
          answer_value: 'resident',
          answer_label: 'Australian resident',
          editable: true,
        },
        {
          question_id: 'employment_type',
          question_label: 'Work situation',
          answer_value: 'employee',
          answer_label: 'Employee (PAYG)',
          editable: true,
        },
      ],
    },
  ],
  incomplete_questions: [],
}

beforeEach(() => {
  jest.clearAllMocks()
  invalidateSpy = jest.spyOn(QueryClient.prototype, 'invalidateQueries')
  mockJumpToQuestion.mockResolvedValue({ data: { data: { state: 'in_progress' } } })
})

afterEach(() => {
  invalidateSpy.mockRestore()
})

test('renders answered questions with formatted labels', async () => {
  mockGetInterviewSummary.mockResolvedValue({ data: { data: SUMMARY_DATA } })
  wrap(<InterviewSummary onEdit={jest.fn()} />)
  await waitFor(() => expect(screen.getByText('Residency status')).toBeInTheDocument())
  expect(screen.getByText('Australian resident')).toBeInTheDocument()
  expect(screen.getByText('Work situation')).toBeInTheDocument()
})

test('renders "Your answers" heading', async () => {
  mockGetInterviewSummary.mockResolvedValue({ data: { data: SUMMARY_DATA } })
  wrap(<InterviewSummary onEdit={jest.fn()} />)
  await waitFor(() => expect(screen.getByText(/your answers/i)).toBeInTheDocument())
})

test('Edit button calls jumpToQuestion with question_id', async () => {
  mockGetInterviewSummary.mockResolvedValue({ data: { data: SUMMARY_DATA } })
  const onEdit = jest.fn()
  wrap(<InterviewSummary onEdit={onEdit} />)

  await waitFor(() => expect(screen.getAllByRole('button', { name: /edit/i })[0]).toBeInTheDocument())
  fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[0])

  await waitFor(() => expect(mockJumpToQuestion).toHaveBeenCalledWith('residency', true))
  await waitFor(() => expect(onEdit).toHaveBeenCalled())
  expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['interview', 'session'] })
  expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['interview', 'summary'] })
  expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['readiness'] })
  expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['export-eligibility'] })
})

test('answer value is right-aligned in a three-column grid row', async () => {
  mockGetInterviewSummary.mockResolvedValue({ data: { data: SUMMARY_DATA } })
  wrap(<InterviewSummary onEdit={jest.fn()} />)

  const answerValue = await screen.findByTestId('answer-value-residency')
  const style = window.getComputedStyle(answerValue)
  expect(style.textAlign).toBe('right')

  const row = screen.getByTestId('answer-row-residency')
  expect(row).toHaveStyle({ display: 'grid', gridTemplateColumns: '1fr auto auto' })
})

test('does not render Edit button for non-editable answers', async () => {
  const nonEditableData = {
    sections: [{
      title: 'Your situation',
      answers: [{
        question_id: 'fy_confirm',
        question_label: 'Financial year',
        answer_value: '2024-25',
        answer_label: '2024-25',
        editable: false,
      }],
    }],
  }
  mockGetInterviewSummary.mockResolvedValue({ data: { data: nonEditableData } })
  wrap(<InterviewSummary onEdit={jest.fn()} />)
  await waitFor(() => expect(screen.getByText('Financial year')).toBeInTheDocument())
  expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument()
})

test('renders incomplete questions section and Resume action', async () => {
  mockGetInterviewSummary.mockResolvedValue({
    data: {
      data: {
        ...SUMMARY_DATA,
        incomplete_questions: [
          {
            question_id: 'wfh',
            question_label: 'Did you work from home during this financial year?',
            editable: true,
          },
        ],
      },
    },
  })
  const onEdit = jest.fn()
  wrap(<InterviewSummary onEdit={onEdit} />)

  await waitFor(() => expect(screen.getByText(/some questions still need answers/i)).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /resume/i }))
  await waitFor(() => expect(mockJumpToQuestion).toHaveBeenCalledWith('wfh', true))
  await waitFor(() => expect(onEdit).toHaveBeenCalled())
})
