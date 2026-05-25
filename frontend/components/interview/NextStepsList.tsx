import Link from 'next/link'
import { FileText, TrendingUp, Home, BarChart2, type LucideIcon } from 'lucide-react'

interface NextStepsListProps {
  activatedSkills: string[]
}

interface SkillStep {
  priority: number
  icon: LucideIcon
  title: string
  hint: string
  link: string
}

const SKILL_NEXT_STEPS: Record<string, SkillStep> = {
  employee_tax_au: {
    priority: 1,
    icon: FileText,
    title: 'Upload your PAYG Payment Summary',
    hint: 'Download from myGov → ATO online services',
    link: '/evidence',
  },
  crypto_skill_au: {
    priority: 2,
    icon: TrendingUp,
    title: 'Export your crypto transaction history',
    hint: 'Download CSV from CoinSpot, Binance, or your exchange',
    link: '/evidence',
  },
  wfh: {
    priority: 3,
    icon: Home,
    title: 'Gather your work from home records',
    hint: 'Timesheets, diary, or ATO app records',
    link: '/evidence',
  },
  investment_skill: {
    priority: 4,
    icon: BarChart2,
    title: 'Upload your investment income statements',
    hint: 'Available from your broker or share registry',
    link: '/evidence',
  },
}

export default function NextStepsList({ activatedSkills }: NextStepsListProps) {
  const steps = activatedSkills
    .filter((skill) => skill in SKILL_NEXT_STEPS)
    .map((skill) => ({ skill, ...SKILL_NEXT_STEPS[skill] }))
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 3)

  if (steps.length === 0) return null

  return (
    <ul className="space-y-3">
      {steps.map(({ skill, icon: Icon, title, hint, link }) => (
        <li
          key={skill}
          className="bg-surface border border-border rounded-md shadow-sm p-4 flex items-start gap-4"
        >
          <Icon aria-hidden="true" className="text-accent w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-ui font-semibold text-text-body text-sm">{title}</p>
            <p className="font-body text-text-muted text-sm">{hint}</p>
            <Link
              href={link}
              className="text-accent font-ui text-sm hover:text-accent-hover transition-colors"
            >
              Upload →
            </Link>
          </div>
        </li>
      ))}
    </ul>
  )
}
