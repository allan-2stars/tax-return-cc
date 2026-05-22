import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AskClaudeDrawer from '@/components/review/AskClaudeDrawer'
import * as reviewApi from '@/lib/api/review'

jest.mock('@/lib/api/review')

const mockAskClaude = reviewApi.askClaude as jest.Mock

beforeEach(() => jest.clearAllMocks())

describe('AskClaudeDrawer', () => {
  it('renders as a side drawer with item title', () => {
    render(
      <AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />
    )
    expect(screen.getByText(/ask about work laptop/i)).toBeInTheDocument()
  })

  it('Close button calls onClose', () => {
    const onClose = jest.fn()
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Submit button calls askClaude API with question', async () => {
    mockAskClaude.mockResolvedValue({ data: { data: { answer: 'This is a work expense.' } } })
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Can I claim this?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    expect(mockAskClaude).toHaveBeenCalledWith('item-1', 'Can I claim this?')
  })

  it('renders AI answer after successful response', async () => {
    mockAskClaude.mockResolvedValue({ data: { data: { answer: 'This is a work expense.' } } })
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Can I claim this?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() =>
      expect(screen.getByText('This is a work expense.')).toBeInTheDocument()
    )
  })

  it('shows Disclaimer component below AI response', async () => {
    mockAskClaude.mockResolvedValue({ data: { data: { answer: 'This is a work expense.' } } })
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Can I claim this?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() =>
      expect(screen.getByText(/does not provide final tax advice/i)).toBeInTheDocument()
    )
  })

  it('thread history shows previous exchange after second question', async () => {
    mockAskClaude
      .mockResolvedValueOnce({ data: { data: { answer: 'First answer.' } } })
      .mockResolvedValueOnce({ data: { data: { answer: 'Second answer.' } } })

    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q1' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() => expect(screen.getByText('First answer.')).toBeInTheDocument())

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q2' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    await waitFor(() => expect(screen.getByText('Second answer.')).toBeInTheDocument())

    expect(screen.getByText('First answer.')).toBeInTheDocument()
    expect(screen.getByText('Q1')).toBeInTheDocument()
    expect(screen.getByText('Q2')).toBeInTheDocument()
  })

  it('disables input and button while loading', async () => {
    let resolve!: (v: unknown) => void
    mockAskClaude.mockReturnValue(new Promise((r) => { resolve = r }))
    render(<AskClaudeDrawer itemId="item-1" itemTitle="Work laptop" onClose={jest.fn()} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Q?' } })
    fireEvent.click(screen.getByRole('button', { name: /ask/i }))
    expect(screen.getByRole('textbox')).toBeDisabled()
    resolve({ data: { data: { answer: 'A' } } })
    await waitFor(() => expect(screen.getByRole('textbox')).not.toBeDisabled())
  })
})
