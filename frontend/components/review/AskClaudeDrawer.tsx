interface AskClaudeDrawerProps {
  itemId: string
  itemTitle: string
  onClose: () => void
}

export default function AskClaudeDrawer({ onClose }: AskClaudeDrawerProps) {
  return (
    <div data-testid="ask-claude-drawer">
      <button type="button" onClick={onClose}>Close</button>
    </div>
  )
}
