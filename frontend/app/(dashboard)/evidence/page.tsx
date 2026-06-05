'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { getDocuments, archiveDocument } from '@/lib/api/documents'
import { getEvidenceObligations } from '@/lib/api/evidence'
import { getSession } from '@/lib/api/interview'
import type { DocumentData, EvidenceObligation, InterviewSessionData } from '@/lib/api/types'
import UploadZone from '@/components/evidence/UploadZone'
import DocumentCard from '@/components/evidence/DocumentCard'
import DuplicateModal from '@/components/evidence/DuplicateModal'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { isFYActive } from '@/lib/utils/fy'

function obligationSuggestion(item: EvidenceObligation): string {
  const haystack = `${item.obligation_key} ${item.label} ${item.category ?? ''}`.toLowerCase()
  if (haystack.includes('work_from_home') || haystack.includes('wfh')) {
    return 'Work-from-home log, diary, or timesheet'
  }
  if (haystack.includes('private_health') || haystack.includes('health insurance')) {
    return 'Private health insurance statement'
  }
  if (haystack.includes('bank') || haystack.includes('interest')) {
    return 'Bank interest statement'
  }
  if (haystack.includes('donation')) {
    return 'Donation receipt'
  }
  if (haystack.includes('expense') || haystack.includes('receipt') || haystack.includes('invoice')) {
    return 'Work expense receipt or invoice'
  }
  return item.label
}

function uploadSuggestions(obligations: EvidenceObligation[]): string[] {
  const relevant = obligations.filter((item) => item.status === 'missing' || item.status === 'partially_matched')
  const unique = new Set<string>()
  relevant.forEach((item) => unique.add(obligationSuggestion(item)))
  return Array.from(unique).slice(0, 6)
}

export default function EvidencePage() {
  const queryClient = useQueryClient()
  const { financialYear } = useWorkspaceStore()
  const [duplicateDocId, setDuplicateDocId] = useState<string | null>(null)

  const { data: documents, isLoading, isError } = useQuery<DocumentData[]>({
    queryKey: ['documents'],
    queryFn: () => getDocuments().then((r) => r.data.data),
  })
  const { data: obligationsData } = useQuery({
    queryKey: ['evidence', 'obligations'],
    queryFn: () => getEvidenceObligations().then((r) => r.data.data),
  })
  const { data: interviewSession } = useQuery<InterviewSessionData>({
    queryKey: ['interview', 'session'],
    queryFn: () => getSession().then((r) => r.data.data),
  })

  const removeMutation = useMutation({
    mutationFn: archiveDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const handleUploadComplete = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
  }

  const fyActive = financialYear ? isFYActive(financialYear) : false
  const suggestions = uploadSuggestions(obligationsData?.obligations ?? [])
  const hasSkippedJourneyAnswers = Boolean(interviewSession?.has_incomplete_questions)

  if (isLoading) {
    return (
      <div className="space-y-8 animate-pulse" aria-label="Loading">
        <div className="h-8 w-48 bg-surface rounded" />
        <div className="bg-surface border border-border rounded-lg h-32" />
        {[1, 2].map((i) => (
          <div key={i} className="bg-surface rounded-lg p-4 h-16" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-risk-high">
          Unable to load documents. Please try refreshing.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text-primary">
          Supporting Evidence
        </h1>
        <p className="text-sm font-ui text-text-muted mt-1">
          Upload tax documents to build your evidence package.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-surface p-5 space-y-3">
        {suggestions.length > 0 ? (
          <>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-ui font-semibold text-text-primary">Recommended to upload now</h2>
              <Link href="/readiness/missing" className="text-sm font-ui text-accent hover:underline">
                Review missing evidence
              </Link>
            </div>
            <ul className="space-y-2">
              {suggestions.map((suggestion) => (
                <li key={suggestion} className="text-sm font-ui text-text-body">
                  {suggestion}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <h2 className="text-sm font-ui font-semibold text-text-primary">What you can upload</h2>
            <p className="text-sm font-ui text-text-muted">
              You can upload documents such as income statements, bank interest statements, receipts, donation receipts, private health insurance statements, and work-from-home evidence.
            </p>
            <p className="text-sm font-ui text-text-muted">
              More specific suggestions will appear after you answer more journey questions or review extracted items.
            </p>
          </>
        )}
      </div>

      {hasSkippedJourneyAnswers && (
        <div className="rounded-md border border-review bg-review-bg px-4 py-3">
          <p className="text-sm font-ui text-text-body">
            Some skipped journey answers may reveal more evidence requirements later.
          </p>
          <Link href="/journey" className="mt-2 inline-block text-sm font-ui text-accent hover:underline">
            Review skipped journey answers
          </Link>
        </div>
      )}

      {fyActive && (
        <div className="bg-review-bg rounded-md px-4 py-3">
          <p className="text-sm font-ui text-review">
            Some documents (like PAYG summaries) are only available after 30 June.
            Upload what you have now.
          </p>
        </div>
      )}

      <UploadZone
        onUploadComplete={handleUploadComplete}
        onDuplicate={(existingId) => setDuplicateDocId(existingId)}
      />

      {documents && documents.length === 0 ? (
        <p className="text-sm font-ui text-text-muted text-center py-12">
          Upload your first document to get started
        </p>
      ) : (
        <div className="space-y-3">
          {documents?.map((doc) => (
            <DocumentCard
              key={doc.document_id}
              document={doc}
              onRemove={(id) => removeMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      {duplicateDocId && (
        <DuplicateModal
          existingDocumentId={duplicateDocId}
          onClose={() => setDuplicateDocId(null)}
        />
      )}
    </div>
  )
}
