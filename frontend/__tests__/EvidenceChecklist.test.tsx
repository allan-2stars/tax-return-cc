import { fireEvent, render, screen, within } from '@testing-library/react'
import EvidenceChecklist from '@/components/readiness/EvidenceChecklist'
import type { EvidenceObligation } from '@/lib/api/types'

const obligations: EvidenceObligation[] = [
  {
    id: 'o1',
    workspace_id: 'ws1',
    financial_year: '2024-25',
    source_type: 'profile',
    source_id: null,
    obligation_key: 'private_health_annual_statement',
    category: 'private_health',
    label: 'Private Health Insurance Annual Statement',
    description: null,
    required_level: 'required',
    status: 'missing',
    reason: 'Private Health Insurance is enabled in your profile.',
    explanation: {
      explanation_id: 'evidence_obligation:o1',
      target_type: 'evidence_obligation',
      target_id: 'o1',
      category: 'evidence_requirement',
      plain_english_summary: 'A private health statement is expected.',
      why_it_matters: 'It helps verify private health details.',
      what_user_should_check: 'Check policy period and statement year.',
      evidence_expected: ['private health annual statement'],
      confidence_level: 'high',
      rule_version: '2026.1',
      source: 'rule',
    },
    matches: [],
    metadata_json: {},
    created_at: null,
    updated_at: null,
  },
  {
    id: 'o2',
    workspace_id: 'ws1',
    financial_year: '2024-25',
    source_type: 'tax_event',
    source_id: null,
    obligation_key: 'bank_interest_statement',
    category: 'bank_interest',
    label: 'Bank Interest Statement',
    description: null,
    required_level: 'recommended',
    status: 'partially_matched',
    reason: 'Bank interest events are present.',
    explanation: {
      explanation_id: 'evidence_obligation:o2',
      target_type: 'evidence_obligation',
      target_id: 'o2',
      category: 'evidence_requirement',
      plain_english_summary: 'A bank interest statement is recommended.',
      why_it_matters: 'It helps validate interest totals.',
      what_user_should_check: 'Check bank name, period, and amount.',
      evidence_expected: ['bank interest statement'],
      confidence_level: 'medium',
      rule_version: '2026.1',
      source: 'rule',
    },
    matches: [
      {
        id: 'm1',
        match_type: 'document',
        status: 'candidate',
        confidence: 0.8,
        reason: 'Document type indicates bank-interest supporting statement.',
        document: {
          id: 'd1',
          original_filename: 'bank-july.pdf',
          document_type: 'bank_statement',
          status: 'ready',
        },
        tax_event: null,
      },
    ],
    metadata_json: {},
    created_at: null,
    updated_at: null,
  },
  {
    id: 'o3',
    workspace_id: 'ws1',
    financial_year: '2024-25',
    source_type: 'tax_event',
    source_id: null,
    obligation_key: 'work_expense_receipt',
    category: 'work_expense',
    label: 'Work-Related Expense Receipt',
    description: null,
    required_level: 'required',
    status: 'matched',
    reason: 'Work-related expense events are present.',
    explanation: {
      explanation_id: 'evidence_obligation:o3',
      target_type: 'evidence_obligation',
      target_id: 'o3',
      category: 'evidence_requirement',
      plain_english_summary: 'A work expense receipt is expected.',
      why_it_matters: 'It supports deduction review quality.',
      what_user_should_check: 'Check vendor, date, and amount.',
      evidence_expected: ['receipt', 'invoice'],
      confidence_level: 'high',
      rule_version: '2026.1',
      source: 'rule',
    },
    matches: [
      {
        id: 'm2',
        match_type: 'tax_event',
        status: 'accepted',
        confidence: 0.95,
        reason: 'Accepted by reviewer.',
        document: null,
        tax_event: {
          id: 'e1',
          event_type: 'deduction',
          category: 'work_expense',
          status: 'confirmed',
        },
      },
    ],
    metadata_json: {},
    created_at: null,
    updated_at: null,
  },
]

describe('EvidenceChecklist', () => {
  it('renders empty state when no obligations exist', () => {
    render(<EvidenceChecklist obligations={[]} />)
    expect(screen.getByText(/No checklist items yet/i)).toBeInTheDocument()
  })

  it('renders grouped categories and statuses', () => {
    render(<EvidenceChecklist obligations={obligations} />)
    expect(screen.getByText('private health')).toBeInTheDocument()
    expect(screen.getByText('bank interest')).toBeInTheDocument()
    expect(screen.getByText('work expense')).toBeInTheDocument()
    expect(screen.getByText('Missing')).toBeInTheDocument()
    expect(screen.getByText('Partially matched')).toBeInTheDocument()
    expect(screen.getByText('Matched')).toBeInTheDocument()
  })

  it('renders candidate wording and matched document details', () => {
    render(<EvidenceChecklist obligations={obligations} onDecideMatch={jest.fn()} />)
    expect(screen.getByText(/Possible match found:/i)).toBeInTheDocument()
    expect(screen.getByText(/bank-july.pdf/i)).toBeInTheDocument()
    expect(screen.getByText(/bank_statement/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /accept match/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reject match/i })).toBeInTheDocument()
  })

  it('renders matched tax event details', () => {
    render(<EvidenceChecklist obligations={obligations} />)
    expect(screen.getByText(/Matched by:/i)).toBeInTheDocument()
    expect(screen.getByText(/work_expense \(deduction, confirmed\)/i)).toBeInTheDocument()
  })

  it('renders explanation and rule version when expanded', () => {
    render(<EvidenceChecklist obligations={obligations} />)
    expect(screen.getByText(/a private health statement is expected/i)).toBeInTheDocument()
    const toggles = screen.getAllByRole('button', { name: /why this matters/i })
    expect(toggles.length).toBeGreaterThan(0)
    fireEvent.click(toggles[0])
    const details = screen.getByTestId('evidence-explanation-o2')
    expect(within(details).getByText(/rule version:/i)).toBeInTheDocument()
    expect(within(details).getByText(/2026\.1/i)).toBeInTheDocument()
    expect(within(details).getByText(/expected evidence:/i)).toBeInTheDocument()
  })

  it('renders rejected match wording', () => {
    const rejected: EvidenceObligation[] = [
      {
        ...obligations[1],
        id: 'o4',
        matches: [
          {
            ...obligations[1].matches[0],
            id: 'm3',
            status: 'rejected',
          },
        ],
      },
    ]
    render(<EvidenceChecklist obligations={rejected} />)
    expect(screen.getByText(/Rejected match:/i)).toBeInTheDocument()
  })
})
