export default function Disclaimer() {
  return (
    <p
      style={{
        color: 'var(--color-text-muted)',
        fontSize: 'var(--text-xs)',
        lineHeight: '1.5',
        borderTop: '1px solid var(--color-border)',
        paddingTop: 'var(--space-3)',
        marginTop: 'var(--space-3)',
      }}
    >
      AI suggestions are supporting evidence only — not financial or tax advice.
      Always review with a registered tax agent before lodging.
    </p>
  )
}
