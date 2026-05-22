import { render, screen, fireEvent } from '@testing-library/react'
import ExportHistoryCard from '@/components/export/ExportHistoryCard'
import type { ExportRecord } from '@/lib/api/types'

function makeRecord(status: string): ExportRecord {
  return {
    id: 'exp-1',
    workspace_id: 'ws-1',
    financial_year: '2024-25',
    readiness_pct: 82.5,
    confirmed_count: 10,
    review_count: 2,
    agent_count: 0,
    missing_count: 1,
    status: status as ExportRecord['status'],
    file_size_bytes: 1024 * 512,
    expires_at: '2026-05-23T10:00:00+00:00',
    created_at: '2026-05-22T10:00:00+00:00',
  }
}

describe('ExportHistoryCard', () => {
  it('renders ready state with download button', () => {
    const onDownload = jest.fn()
    render(
      <ExportHistoryCard
        record={makeRecord('ready')}
        onDownload={onDownload}
        onRegenerate={jest.fn()}
      />
    )
    expect(screen.getByText(/2024-25/)).toBeInTheDocument()
    expect(screen.getByText(/82/)).toBeInTheDocument()
    const btn = screen.getByText(/download/i)
    fireEvent.click(btn)
    expect(onDownload).toHaveBeenCalledWith('exp-1')
  })

  it('renders expired state with re-generate button', () => {
    const onRegenerate = jest.fn()
    render(
      <ExportHistoryCard
        record={makeRecord('expired')}
        onDownload={jest.fn()}
        onRegenerate={onRegenerate}
      />
    )
    const btn = screen.getByText(/re-generate/i)
    fireEvent.click(btn)
    expect(onRegenerate).toHaveBeenCalledWith('exp-1')
  })

  it('renders generating state with spinner', () => {
    render(
      <ExportHistoryCard
        record={makeRecord('generating')}
        onDownload={jest.fn()}
        onRegenerate={jest.fn()}
      />
    )
    expect(screen.getByTestId('history-generating-spinner')).toBeInTheDocument()
  })
})
