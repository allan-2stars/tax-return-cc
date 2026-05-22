'use client'
import { useQuery } from '@tanstack/react-query'
import { getAbout, exportDiagnosticLog } from '@/lib/api/settings'
import Disclaimer from '@/components/shared/Disclaimer'

export default function AboutTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['settings-about'],
    queryFn: () => getAbout().then((r) => r.data.data),
  })

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Tax Return AI
        </h2>
        <p className="text-sm font-ui text-text-muted">M10 — Phase 7</p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Active skills
        </h2>
        {isLoading ? (
          <p className="text-sm font-ui text-text-muted">Loading…</p>
        ) : (
          <div className="space-y-2">
            {data?.active_skills.map((skill) => (
              <div
                key={skill.skill_id}
                className="flex items-center justify-between text-sm font-ui"
              >
                <span className="text-text-body font-mono">{skill.skill_id}</span>
                <span className="text-text-muted">
                  v{skill.version}{' '}
                  <span className="text-ready">✓ Active</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold text-text-primary">
          Disclaimer
        </h2>
        <Disclaimer />
      </section>

      <section>
        <button
          type="button"
          onClick={() => exportDiagnosticLog()}
          className="text-sm font-ui text-accent underline"
        >
          Export diagnostic log
        </button>
      </section>
    </div>
  )
}
