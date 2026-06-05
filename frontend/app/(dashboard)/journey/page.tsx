'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  startInterview, answerQuestion, completeInterview,
  restartInterview,
  goBack, cancelEdit, skipQuestion, getYoySuggestions, actOnSuggestion,
} from '@/lib/api/interview'
import type { InterviewSessionData, YoYSuggestion } from '@/lib/api/types'
import QuestionCard from '@/components/interview/QuestionCard'
import ProgressDots from '@/components/interview/ProgressDots'
import YoYSuggestionCard from '@/components/interview/YoYSuggestionCard'
import useInterviewStore from '@/lib/stores/interview.store'
import { useInterview } from '@/lib/hooks/useInterview'
import Disclaimer from '@/components/shared/Disclaimer'
import NextStepsList from '@/components/interview/NextStepsList'
import InterviewSummary from '@/components/interview/InterviewSummary'
import { normalizeApiError } from '@/lib/api/errors'

export default function JourneyPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { newSkillPending, setNewSkillPending } = useInterviewStore()

  const { data, isLoading, isError } = useInterview()
  const [serverError, setServerError] = useState<string | null>(null)
  const [sessionError, setSessionError] = useState(false)

  useEffect(() => {
    setServerError(null)
    setSessionError(false)
  }, [data?.current_question?.id])

  const { data: yoy } = useQuery<YoYSuggestion[]>({
    queryKey: ['yoy', 'suggestions'],
    queryFn: () => getYoySuggestions().then((r) => r.data.data),
    enabled: data?.state === 'awaiting_evidence' || data?.state === 'complete',
  })

  const patch = (p: Partial<InterviewSessionData>) =>
    queryClient.setQueryData<InterviewSessionData>(
      ['interview', 'session'],
      (old): InterviewSessionData | undefined => (old ? { ...old, ...p } : undefined)
    )

  const invalidateJourneyDerived = () => {
    queryClient.invalidateQueries({ queryKey: ['interview', 'session'] })
    queryClient.invalidateQueries({ queryKey: ['interview', 'summary'] })
    queryClient.invalidateQueries({ queryKey: ['readiness'] })
    queryClient.invalidateQueries({ queryKey: ['export-eligibility'] })
  }

  const startMutation = useMutation({
    mutationFn: startInterview,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interview', 'session'] }),
  })

  const restartMutation = useMutation({
    mutationFn: restartInterview,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interview', 'session'] }),
  })

  const answerMutation = useMutation({
    mutationFn: ({ question_id, answer }: { question_id: string; answer: string }) =>
      answerQuestion(question_id, answer),
    onSuccess: async (res) => {
      setServerError(null)
      const d = res.data.data
      const prev = data?.activated_skills ?? []
      const newSkill = d.activated_skills.find((s) => !prev.includes(s))
      if (newSkill) setNewSkillPending(newSkill)

      // Edit mode: server already set state=awaiting_evidence — skip completeInterview
      if (d.state === 'awaiting_evidence') {
        patch({
          state: 'awaiting_evidence',
          current_question: null,
          activated_skills: d.activated_skills,
          progress: d.progress,
          edit_mode: d.edit_mode,
          edit_target: d.edit_target,
          edit_flow_completed: d.edit_flow_completed,
          edit_flow_total: d.edit_flow_total,
        })
        invalidateJourneyDerived()
        return
      }

      if (d.next_question === null) {
        const completeRes = await completeInterview()
        patch({
          state: completeRes.data.data.state,
          current_question: null,
          activated_skills: d.activated_skills,
          progress: d.progress,
        })
        invalidateJourneyDerived()
        return
      }

      patch({
        state: d.state,
        current_question: d.next_question, // answer response uses next_question; cache uses current_question
        activated_skills: d.activated_skills,
        progress: d.progress,
        edit_mode: d.edit_mode,
        edit_target: d.edit_target,
        edit_flow_completed: d.edit_flow_completed,
        edit_flow_total: d.edit_flow_total,
      })
      invalidateJourneyDerived()
    },
    onError: (err: unknown) => {
      const error = normalizeApiError(err, 'Unable to save answer right now. Please try again.')
      setServerError(error.message)
      setSessionError(error.kind === 'session')
    },
  })

  const backMutation = useMutation({
    mutationFn: goBack,
    onSuccess: (res) => patch(res.data.data),
  })

  const cancelEditMutation = useMutation({
    mutationFn: cancelEdit,
    onSuccess: (res) => {
      patch(res.data.data)
      invalidateJourneyDerived()
    },
  })

  const skipMutation = useMutation({
    mutationFn: ({ question_id, reason }: { question_id: string; reason: string }) =>
      skipQuestion(question_id, reason),
    onSuccess: (res) => {
      const d = res.data.data
      patch({ state: d.state, current_question: d.next_question, progress: d.progress })
      invalidateJourneyDerived()
    },
    onError: (err: unknown) => {
      const error = normalizeApiError(err, 'Unable to skip this question right now. Please try again.')
      setServerError(error.message)
      setSessionError(error.kind === 'session')
    },
  })

  const yoyMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => actOnSuggestion(id, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['yoy', 'suggestions'] }),
  })

  const isBusy = answerMutation.isPending || backMutation.isPending || cancelEditMutation.isPending || skipMutation.isPending

  if (isLoading) return <div className="p-8 font-ui text-text-muted">Loading your tax journey...</div>
  if (isError || !data) return <div className="p-8 font-ui text-risk-high">Unable to load your tax journey. Please refresh the page.</div>

  const displayProgress = data.edit_mode
    ? {
        completed: data.edit_flow_completed ?? 0,
        total: data.edit_flow_total ?? 1,
      }
    : data.progress

  const isAtEditRoot = Boolean(
    data.edit_mode && (data.edit_flow_completed ?? 0) === 0
  )
  const canGoBack = data.edit_mode || (data.progress.completed ?? 0) > 0

  return (
    <div className="max-w-xl mx-auto px-4 py-8 space-y-6">

      {newSkillPending && (
        <div className="bg-accent-soft border border-accent rounded-md p-4 flex items-start justify-between gap-4">
          <div>
            <p className="font-ui font-medium text-text-primary">We found something new in your tax profile</p>
            <p className="text-sm font-body text-text-muted">A few more questions needed.</p>
          </div>
          <button
            type="button"
            onClick={() => setNewSkillPending(null)}
            className="text-sm font-ui font-medium text-accent hover:text-accent-hover whitespace-nowrap transition-colors"
          >
            Continue →
          </button>
        </div>
      )}

      {data.state === 'not_started' && (
        <div className="space-y-6 pt-8">
          <div className="space-y-3">
            <h1 className="font-display text-3xl text-text-primary">Start your tax journey</h1>
            <p className="font-body text-text-muted">
              We'll ask you a few questions to personalise your tax preparation experience.
            </p>
          </div>
          <button
            type="button"
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending}
            className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {startMutation.isPending ? 'Starting...' : 'Get started →'}
          </button>
        </div>
      )}

      {(data.state === 'in_progress' || data.state === 'paused') && data.current_question && (
        <div className="space-y-6">
          <ProgressDots completed={displayProgress.completed} total={displayProgress.total} />
          <QuestionCard
            question={data.current_question}
            onAnswer={(qid, ans) => answerMutation.mutate({ question_id: qid, answer: ans })}
            onBack={() => {
              if (isAtEditRoot) {
                cancelEditMutation.mutate()
                return
              }
              backMutation.mutate()
            }}
            onSkip={(qid) => skipMutation.mutate({ question_id: qid, reason: 'user_skipped' })}
            canGoBack={canGoBack}
            isSubmitting={isBusy}
            currentAnswer={data.answers?.[data.current_question.id]}
            serverError={serverError}
            editMode={data.edit_mode}
          />
          {sessionError && (
            <Link href="/login?returnTo=/journey" className="text-sm font-ui text-accent underline">
              Sign in again
            </Link>
          )}
        </div>
      )}

      {(data.state === 'in_progress' || data.state === 'paused') && !data.current_question && (
        <div className="space-y-6">
          <p className="font-ui text-sm text-risk-high">Some questions still need answers.</p>
          <InterviewSummary onEdit={() => {}} />
        </div>
      )}

      {(data.state === 'awaiting_evidence' || data.state === 'complete') && (
        <div className="space-y-10">
          {/* Heading */}
          {data.needs_restart ? (
            <div className="space-y-3">
              <h1 className="font-display text-3xl text-text-primary">Your Tax Journey needs attention</h1>
              <p className="font-body text-text-muted">
                Some interview answers are incomplete or inconsistent. Restarting will not remove uploaded documents or review data.
              </p>
              <button
                type="button"
                onClick={() => restartMutation.mutate()}
                disabled={restartMutation.isPending}
                className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
              >
                {restartMutation.isPending ? 'Restarting...' : 'Restart Tax Journey'}
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <h1 className="font-display text-3xl text-text-primary">You're all set up</h1>
              <p className="font-body text-lg text-text-muted">Here's what to do next</p>
            </div>
          )}

          {data.needs_restart && <Disclaimer />}

          {/* YoY suggestions (keep existing) */}
          {!data.needs_restart && yoy && yoy.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-ui font-medium text-text-muted uppercase tracking-wide">From last year</h2>
              {yoy.slice(0, 3).map((s) => (
                <YoYSuggestionCard
                  key={s.id}
                  suggestion={s}
                  onAction={(id, action) => yoyMutation.mutate({ id, action })}
                />
              ))}
            </div>
          )}

          {/* Personalised next steps */}
          {!data.needs_restart && <NextStepsList activatedSkills={data.activated_skills ?? []} />}

          {/* Answer summary + edit flow */}
          {!data.needs_restart && (
            <InterviewSummary
              onEdit={() => {}}
            />
          )}

          {/* CTAs */}
          {!data.needs_restart && <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={() => router.push('/readiness')}
              className="px-6 py-3 rounded-md bg-accent text-surface font-ui font-medium hover:bg-accent-hover transition-colors"
            >
              Go to Tax Readiness →
            </button>
            <button
              type="button"
              onClick={() => router.push('/evidence')}
              className="px-6 py-3 font-ui font-medium text-text-muted hover:text-text-body transition-colors"
            >
              Upload documents →
            </button>
          </div>}

          {!data.needs_restart && <Disclaimer />}
        </div>
      )}
    </div>
  )
}
