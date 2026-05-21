'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDocuments, archiveDocument } from '@/lib/api/documents'
import type { DocumentData } from '@/lib/api/types'
import UploadZone from '@/components/evidence/UploadZone'
import DocumentCard from '@/components/evidence/DocumentCard'
import DuplicateModal from '@/components/evidence/DuplicateModal'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import { isFYActive } from '@/lib/utils/fy'

export default function EvidencePage() {
  const queryClient = useQueryClient()
  const { financialYear } = useWorkspaceStore()
  const [duplicateDocId, setDuplicateDocId] = useState<string | null>(null)

  const { data: documents, isLoading, isError } = useQuery<DocumentData[]>({
    queryKey: ['documents'],
    queryFn: () => getDocuments().then((r) => r.data.data),
  })

  const removeMutation = useMutation({
    mutationFn: archiveDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  })

  const handleUploadComplete = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
  }

  const fyActive = financialYear ? isFYActive(financialYear) : false

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm font-ui text-text-muted">Loading your documents…</p>
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
