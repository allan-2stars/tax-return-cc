'use client'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSession, startInterview, answerQuestion,
  goBack, skipQuestion, getYoySuggestions, actOnSuggestion,
} from '@/lib/api/interview'
import type { InterviewSessionData, YoYSuggestion } from '@/lib/api/types'
import QuestionCard from '@/components/interview/QuestionCard'
import ProgressDots from '@/components/interview/ProgressDots'
import YoYSuggestionCard from '@/components/interview/YoYSuggestionCard'
import useInterviewStore from '@/lib/stores/interview.store'

const NEXT_STEPS: Record<string, { label: string; hint: string }> = {
  employee_tax_au: {
    label: 'Upload your PAYG Payment Summary',
    hint: 'Download from myGov → ATO online services',
  },
  wfh_skill: {
    label: 'Gather your WFH records',
    hint: 'Timesheets, diary, or ATO app records',
  },
  investment_skill: {
    label: 'Export your investment statement',
    hint: 'Download from your broker or share registry',
  },
  crypto_skill_au: {
    label: 'Export your crypto transaction history',
    hint: 'Download CSV from CoinSpot or your exchange',
  },
}

export default function JourneyPage() {
  const queryClient = useQueryClient()
  const { newSkillPending, setNewSkillPending } = useInterviewStore()

  const { data, isLoading, isError } = useQuery<InterviewSessionData>({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })

  const { data: yoy } = useQuery<YoYSuggestion[]>({
    queryKey: ['yoy', 'suggestions'],
    queryFn: () => getYoySuggestions().then((r) => r.data.data),
    enabled: data?.state === 'awaiting_evidence' || data?.state === 'complete',
  })

  const patch = (p: Partial<InterviewSessionData>) =>
    queryClient.setQueryData<InterviewSessionData>(['interview', 'session'], (old) =>
      old ? { ...old, ...p } : old
    )

  const startMutation = useMutation({
    mutationFn: startInterview,
    onSuccess: (res) => patch(res.data.data),
  })

  const answerMutation = useMutation({
    mutationFn: ({ question_id, answer }: { question_id: string; answer: string }) =>
      answerQuestion(question_id, answer),
    onSuccess: (res) => {
      const d = res.data.data
      const prev = data?.activated_skills ?? []
      const newSkill = d.activated_skills.find((s) => !prev.includes(s))
      if (newSkill) setNewSkillPending(newSkill)
      patch({ state: d.state, current_question: d.next_question, activated_skills: d.activated_skills, progress: d.progress })
    },
  })

  const backMutation = useMutation({
    mutationFn: goBack,
    onSuccess: (res) => patch(res.data.data),
  })

  const skipMutation = useMutation({
    mutationFn: ({ question_id, reason }: { question_id: string; reason: string }) =>
      skipQuestion(question_id, reason),
    onSuccess: (res) => {
      const d = res.data.data
      patch({ state: d.state, current_question: d.next_question, progress: d.progress })
    },
  })

  const yoyMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => actOnSuggestion(id, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['yoy', 'suggestions'] }),
  })

  const isBusy = answerMutation.isPending || backMutation.isPending || skipMutation.isPending

  if (isLoading) return <div className="p-8 font-ui text-text-muted">Loading...</div>
  if (isError || !data) return <div className="p-8 font-ui text-risk-high">Unable to load your tax journey.</div>

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
          <ProgressDots completed={data.progress.completed} total={data.progress.total} />
          <QuestionCard
            question={data.current_question}
            onAnswer={(qid, ans) => answerMutation.mutate({ question_id: qid, answer: ans })}
            onBack={() => backMutation.mutate()}
            onSkip={(qid) => skipMutation.mutate({ question_id: qid, reason: 'user_skipped' })}
            isSubmitting={isBusy}
          />
        </div>
      )}

      {data.state === 'awaiting_evidence' && (
        <div className="space-y-8">
          <div className="space-y-3">
            <h1 className="font-display text-3xl text-text-primary">You're all set up</h1>
            <p className="font-body text-text-muted">Here's what to gather next based on your profile:</p>
          </div>
          <ul className="space-y-3">
            {(data.activated_skills ?? []).slice(0, 3).map((skillId) => {
              const step = NEXT_STEPS[skillId]
              if (!step) return null
              return (
                <li key={skillId} className="bg-surface border border-border rounded-md p-4 space-y-1">
                  <p className="font-ui font-medium text-text-body">{step.label}</p>
                  <p className="text-sm font-body text-text-muted">{step.hint}</p>
                </li>
              )
            })}
          </ul>
          {yoy && yoy.length > 0 && (
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
          <Link
            href="/readiness"
            className="inline-block px-6 py-3 rounded-md bg-ready text-surface font-ui font-medium hover:opacity-90 transition-opacity"
          >
            View your readiness →
          </Link>
        </div>
      )}

      {data.state === 'complete' && (
        <div className="space-y-6 pt-8">
          <div className="space-y-3">
            <h1 className="font-display text-3xl text-text-primary">Interview complete</h1>
            <p className="font-body text-text-muted">
              Your tax profile is set up. Check your readiness score to see what's next.
            </p>
          </div>
          <Link
            href="/readiness"
            className="inline-block text-accent font-ui font-medium hover:text-accent-hover transition-colors"
            aria-label="View your tax readiness"
          >
            View your tax readiness →
          </Link>
        </div>
      )}
    </div>
  )
}
