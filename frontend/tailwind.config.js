/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      // ── Colors — all map to CSS variables from globals.css ─────────────────
      colors: {
        canvas:           'var(--color-canvas)',
        surface:          'var(--color-surface)',
        'surface-raised': 'var(--color-surface-raised)',
        border:           'var(--color-border)',
        'border-strong':  'var(--color-border-strong)',

        'text-primary':   'var(--color-text-primary)',
        'text-body':      'var(--color-text-body)',
        'text-muted':     'var(--color-text-muted)',
        'text-faint':     'var(--color-text-faint)',

        accent:           'var(--color-accent)',
        'accent-hover':   'var(--color-accent-hover)',
        'accent-soft':    'var(--color-accent-soft)',

        ready:            'var(--color-ready)',
        'ready-bg':       'var(--color-ready-bg)',
        review:           'var(--color-review)',
        'review-bg':      'var(--color-review-bg)',
        agent:            'var(--color-agent)',
        'agent-bg':       'var(--color-agent-bg)',
        'risk-high':      'var(--color-risk-high)',
        'risk-bg':        'var(--color-risk-bg)',

        'progress-track': 'var(--color-progress-track)',
        'progress-fill':  'var(--color-progress-fill)',
      },

      // ── Font families ───────────────────────────────────────────────────────
      fontFamily: {
        display: ['var(--font-display)'],
        body:    ['var(--font-body)'],
        ui:      ['var(--font-ui)'],
        mono:    ['var(--font-mono)'],
      },

      // ── Type scale — sizes from CSS vars, line-heights from DESIGN.md ───────
      fontSize: {
        'xs':   ['var(--text-xs)',   { lineHeight: '1rem'   }],
        'sm':   ['var(--text-sm)',   { lineHeight: '1.25rem'}],
        'base': ['var(--text-base)', { lineHeight: '1.6rem' }],
        'lg':   ['var(--text-lg)',   { lineHeight: '1.6rem' }],
        'xl':   ['var(--text-xl)',   { lineHeight: '1.4rem' }],
        '2xl':  ['var(--text-2xl)',  { lineHeight: '1.3rem' }],
        '3xl':  ['var(--text-3xl)',  { lineHeight: '1.2rem' }],
        '4xl':  ['var(--text-4xl)',  { lineHeight: '1.1rem' }],
      },

      // ── Spacing — maps p-1…p-20 to --space-* CSS variables ─────────────────
      spacing: {
        '1':  'var(--space-1)',
        '2':  'var(--space-2)',
        '3':  'var(--space-3)',
        '4':  'var(--space-4)',
        '5':  'var(--space-5)',
        '6':  'var(--space-6)',
        '8':  'var(--space-8)',
        '10': 'var(--space-10)',
        '12': 'var(--space-12)',
        '16': 'var(--space-16)',
        '20': 'var(--space-20)',
      },

      // ── Border radius ───────────────────────────────────────────────────────
      borderRadius: {
        'sm':   'var(--radius-sm)',
        'md':   'var(--radius-md)',
        'lg':   'var(--radius-lg)',
        'xl':   'var(--radius-xl)',
        'full': 'var(--radius-full)',
      },

      // ── Box shadows ─────────────────────────────────────────────────────────
      boxShadow: {
        'sm':    'var(--shadow-sm)',
        'md':    'var(--shadow-md)',
        'lg':    'var(--shadow-lg)',
        'focus': 'var(--shadow-focus)',
      },
    },
  },
  plugins: [],
}
