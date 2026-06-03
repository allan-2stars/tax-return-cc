'use client'

import { useEffect, useMemo, useState } from 'react'

interface UseSessionDraftOptions<T extends object> {
  keyParts: Array<string | null | undefined>
  draft: T
  hasContent: (draft: T) => boolean
  applyDraft: (draft: T) => void
  parseDraft?: (value: string | null) => T | null
}

function defaultParseDraft<T extends object>(value: string | null): T | null {
  if (!value) return null
  try {
    const parsed = JSON.parse(value)
    if (!parsed || typeof parsed !== 'object') return null
    return parsed as T
  } catch {
    return null
  }
}

function normalizeKeyPart(value: string | null | undefined): string {
  return encodeURIComponent(value || 'unknown')
}

export function useSessionDraft<T extends object>({
  keyParts,
  draft,
  hasContent,
  applyDraft,
  parseDraft = defaultParseDraft,
}: UseSessionDraftOptions<T>) {
  const [notice, setNotice] = useState<'found' | 'saved' | null>(null)
  const [restoredDraft, setRestoredDraft] = useState<T | null>(null)
  const [draftLoaded, setDraftLoaded] = useState(false)
  const [saveSuppressed, setSaveSuppressed] = useState(false)

  const draftKey = useMemo(
    () => `tax-return-draft:${keyParts.map(normalizeKeyPart).join(':')}`,
    [keyParts]
  )
  const serializedDraft = useMemo(() => JSON.stringify(draft), [draft])
  const hasChanges = hasContent(draft) && !saveSuppressed

  useEffect(() => {
    setDraftLoaded(false)
    setSaveSuppressed(false)
    setRestoredDraft(null)
    setNotice(null)

    const stored = parseDraft(sessionStorage.getItem(draftKey))
    if (stored && hasContent(stored)) {
      setRestoredDraft(stored)
      setNotice('found')
    }
    setDraftLoaded(true)
  }, [draftKey, hasContent, parseDraft])

  useEffect(() => {
    if (!draftLoaded || restoredDraft || saveSuppressed) return
    if (!hasContent(draft)) return

    sessionStorage.setItem(draftKey, serializedDraft)
    setNotice('saved')
  }, [draftLoaded, restoredDraft, saveSuppressed, hasContent, draft, draftKey, serializedDraft])

  useEffect(() => {
    if (!hasChanges) return

    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [hasChanges])

  function restoreDraft() {
    if (!restoredDraft) return
    applyDraft(restoredDraft)
    setRestoredDraft(null)
    setNotice('saved')
  }

  function discardDraft() {
    sessionStorage.removeItem(draftKey)
    setRestoredDraft(null)
    setNotice(null)
  }

  function clearDraft(suppressSave = false) {
    if (suppressSave) setSaveSuppressed(true)
    sessionStorage.removeItem(draftKey)
    setRestoredDraft(null)
    setNotice(null)
  }

  return {
    draftKey,
    notice,
    restoredDraft,
    hasChanges,
    restoreDraft,
    discardDraft,
    clearDraft,
  }
}
