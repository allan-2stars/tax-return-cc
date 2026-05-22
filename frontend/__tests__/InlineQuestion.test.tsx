import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import InlineQuestion from '@/components/review/InlineQuestion'
import type { ReviewItemQuestion } from '@/lib/api/types'

const q1: ReviewItemQuestion = {
  id: 'q1',
  ask: 'Was this expense 100% for work?',
  type: 'single_choice',
  options: ['yes', 'no', 'partially'],
}

const q2: ReviewItemQuestion = {
  id: 'q2',
  ask: 'Do you have a receipt?',
  type: 'single_choice',
  options: ['yes', 'no'],
}

const mockOnAnswer = jest.fn()

beforeEach(() => jest.clearAllMocks())

describe('InlineQuestion', () => {
  it('renders the first question text', () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1, q2]} onAnswer={mockOnAnswer} />)
    expect(screen.getByText('Was this expense 100% for work?')).toBeInTheDocument()
  })

  it('renders option buttons for single_choice', () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />)
    expect(screen.getByRole('button', { name: 'yes' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'no' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'partially' })).toBeInTheDocument()
  })

  it('calls onAnswer with question id and selected option', async () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    await waitFor(() =>
      expect(mockOnAnswer).toHaveBeenCalledWith('q1', 'yes')
    )
  })

  it('advances to second question after first is answered', async () => {
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[q1, q2]} onAnswer={mockOnAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    await waitFor(() =>
      expect(screen.getByText('Do you have a receipt?')).toBeInTheDocument()
    )
    expect(screen.queryByText('Was this expense 100% for work?')).not.toBeInTheDocument()
  })

  it('renders nothing when all questions are answered locally', async () => {
    mockOnAnswer.mockResolvedValue(undefined)
    const { container } = render(
      <InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />
    )
    fireEvent.click(screen.getByRole('button', { name: 'no' }))
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('renders text input for type=text questions', () => {
    const textQ: ReviewItemQuestion = { id: 'q3', ask: 'How many days?', type: 'text', options: null }
    mockOnAnswer.mockResolvedValue(undefined)
    render(<InlineQuestion questions={[textQ]} onAnswer={mockOnAnswer} />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument()
  })

  it('disables option buttons while pending', async () => {
    let resolve!: () => void
    mockOnAnswer.mockReturnValue(new Promise<void>((r) => { resolve = r }))
    render(<InlineQuestion questions={[q1]} onAnswer={mockOnAnswer} />)
    fireEvent.click(screen.getByRole('button', { name: 'yes' }))
    expect(screen.getByRole('button', { name: 'yes' })).toBeDisabled()
    resolve()
  })
})
