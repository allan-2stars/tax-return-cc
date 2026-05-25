'use client'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Info } from 'lucide-react'
import type { InterviewQuestion } from '@/lib/api/types'

const OPTION_LABELS: Record<string, string> = {
  // residency
  resident:              'Australian resident',
  non_resident:          'Non-resident',
  part_year:             'Part-year resident',
  // employment_type
  employee:              'Employee',
  sole_trader:           'Sole trader / self-employed',
  both:                  'Both employee and sole trader',
  // family_situation
  single_no_dependents:  'Single, no dependents',
  has_spouse:            'Has a spouse / partner',
  has_dependents:        'Has dependent children',
  // lodger_type
  self:                  'Self (myTax)',
  agent:                 'Tax agent',
  unknown:               'Not sure yet',
  // spouse_income_range
  under_18200:           'Under $18,200',
  '18200_45000':         '$18,200 – $45,000',
  '45000_120000':        '$45,000 – $120,000',
  over_120000:           'Over $120,000',
  // spouse_novated_lease / generic yes-no-not_sure
  yes:                   'Yes',
  no:                    'No',
  not_sure:              'Not sure',
}

function formatOptionLabel(value: string | number): string {
  const s = String(value)
  return OPTION_LABELS[s] ?? s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

interface Props {
  question: InterviewQuestion
  onAnswer: (questionId: string, answer: string) => void
  onBack: () => void
  onSkip: (questionId: string) => void
  isSubmitting?: boolean
}

export default function QuestionCard({
  question, onAnswer, onBack, onSkip, isSubmitting = false,
}: Props) {
  const [whyOpen, setWhyOpen] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<{ answer: string }>()

  function onNumberSubmit({ answer }: { answer: string }) {
    if (answer.trim()) onAnswer(question.id, answer.trim())
  }

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        disabled={isSubmitting}
        aria-label="Back"
        className="text-sm font-ui text-text-muted hover:text-text-body transition-colors disabled:opacity-50"
      >
        ← Back
      </button>

      {/* Question title row with optional ⓘ icon */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-display text-xl text-text-primary">{question.ask}</h2>
          {question.why && (
            <button
              type="button"
              onClick={() => setWhyOpen((v) => !v)}
              aria-label="Why do we ask?"
              className="flex-shrink-0 mt-1 text-text-muted hover:text-text-body transition-colors"
            >
              <Info size={16} aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Why panel — expands between title and options */}
        {whyOpen && question.why && (
          <div className="rounded-md bg-surface-raised px-4 py-3 text-sm font-ui text-text-body italic">
            {question.why}
          </div>
        )}

        {/* Hint — always visible when present */}
        {question.hint && !question.currency && (
          <p className="text-sm font-ui text-text-muted italic">{question.hint}</p>
        )}
      </div>

      {/* Single-choice options */}
      {question.options && (
        <ul className="space-y-3">
          {question.options.map((opt) => (
            <li key={opt}>
              <button
                type="button"
                onClick={() => onAnswer(question.id, opt)}
                disabled={isSubmitting}
                className="w-full py-4 px-4 text-left rounded-md bg-surface border border-border hover:border-accent text-text-body font-ui transition-colors disabled:opacity-50"
              >
                {formatOptionLabel(opt)}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Currency input */}
      {question.currency && (
        <form onSubmit={handleSubmit(onNumberSubmit)} className="space-y-3">
          <div>
            <div className="relative flex items-center">
              <span className="absolute left-3 text-text-muted font-ui text-sm select-none">$</span>
              <input
                type="number"
                placeholder="0.00"
                disabled={isSubmitting}
                style={{ MozAppearance: 'textfield' } as React.CSSProperties}
                className="w-full pl-7 pr-4 py-3 rounded-md border border-border bg-surface font-mono text-base text-text-primary focus:outline-none focus:border-accent [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                {...register('answer', question.required ? { required: 'Please enter an amount.' } : {})}
              />
            </div>
            {errors.answer && (
              <p role="alert" className="text-sm font-ui text-risk-high mt-1">
                {errors.answer.message}
              </p>
            )}
            {question.hint && (
              <p className="text-sm font-ui text-text-muted italic mt-1">{question.hint}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            Continue
          </button>
        </form>
      )}

      {/* Plain text / number input */}
      {!question.currency && (question.type === 'text' || question.type === 'number') && (
        <form onSubmit={handleSubmit(onNumberSubmit)} className="space-y-3">
          <div>
            <input
              type={question.type === 'number' ? 'number' : 'text'}
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-md bg-surface border border-border focus:border-accent focus:outline-none text-text-body font-ui"
              {...register('answer', question.required ? { required: 'This field is required.' } : {})}
            />
            {errors.answer && (
              <p role="alert" className="text-sm font-ui text-risk-high mt-1">
                {errors.answer.message}
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            Continue
          </button>
        </form>
      )}

      {/* Bottom row: skip only */}
      {!question.required && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => onSkip(question.id)}
            disabled={isSubmitting}
            aria-label="Skip for now"
            className="text-sm font-ui text-text-faint hover:text-text-muted transition-colors whitespace-nowrap disabled:opacity-50"
          >
            Skip for now →
          </button>
        </div>
      )}
    </div>
  )
}
