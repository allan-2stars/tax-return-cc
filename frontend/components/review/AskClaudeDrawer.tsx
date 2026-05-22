'use client'
import { useState } from 'react'
import { askClaude } from '@/lib/api/review'
import Disclaimer from '@/components/shared/Disclaimer'

interface ThreadEntry {
  question: string
  answer: string
}

interface AskClaudeDrawerProps {
  itemId: string
  itemTitle: string
  onClose: () => void
}

export default function AskClaudeDrawer({ itemId, itemTitle, onClose }: AskClaudeDrawerProps) {
  const [input, setInput] = useState('')
  const [thread, setThread] = useState<ThreadEntry[]>([])
  const [loading, setLoading] = useState(false)

  async function handleAsk() {
    const question = input.trim()
    if (!question || loading) return
    setLoading(true)
    try {
      const res = await askClaude(itemId, question)
      const answer = res.data.data.answer
      setThread((prev) => [...prev, { question, answer }])
      setInput('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      data-testid="ask-claude-drawer"
      className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-surface border-l border-border shadow-xl flex flex-col"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h2 className="font-display font-semibold text-base text-text-primary">
          Ask about {itemTitle}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="text-sm font-ui text-text-muted hover:text-text-body transition-colors"
        >
          Close ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {thread.map((entry, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-ui font-medium text-text-body">{entry.question}</p>
            <p className="text-sm font-ui text-text-muted">{entry.answer}</p>
          </div>
        ))}
        {thread.length > 0 && <Disclaimer />}
      </div>

      <div className="px-4 py-3 border-t border-border space-y-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          rows={3}
          placeholder="Ask a question about this item…"
          className="w-full border border-border rounded px-3 py-2 text-sm font-ui bg-surface text-text-body focus:outline-none focus:ring-1 focus:ring-accent resize-none disabled:opacity-50"
        />
        <button
          type="button"
          disabled={loading || !input.trim()}
          onClick={handleAsk}
          className="w-full min-h-11 rounded text-sm font-ui font-medium bg-accent text-surface hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? 'Thinking…' : 'Ask'}
        </button>
      </div>
    </div>
  )
}
