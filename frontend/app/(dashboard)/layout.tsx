// frontend/app/(dashboard)/layout.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Map,
  BarChart2,
  SearchX,
  Briefcase,
  Scissors,
  TrendingUp,
  FolderOpen,
  CheckSquare,
  Package,
  Settings,
  MoreHorizontal,
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import useWorkspaceStore from '@/lib/stores/workspace.store'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ size?: number | string; className?: string }>
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Tax Journey', href: '/journey', icon: Map },
  { label: 'Tax Readiness', href: '/readiness', icon: BarChart2 },
  { label: 'Missing Evidence', href: '/readiness/missing', icon: SearchX },
  { label: 'Income', href: '/review?filter=income', icon: Briefcase },
  { label: 'Deductions', href: '/review?filter=deductions', icon: Scissors },
  { label: 'Investments', href: '/review?filter=investments', icon: TrendingUp },
  { label: 'Supporting Evidence', href: '/evidence', icon: FolderOpen },
  { label: 'Review', href: '/review', icon: CheckSquare },
  { label: 'Export Review Pack', href: '/export', icon: Package },
  { label: 'Settings', href: '/settings', icon: Settings },
]

const MOBILE_TABS: NavItem[] = [
  { label: 'Journey', href: '/journey', icon: Map },
  { label: 'Readiness', href: '/readiness', icon: BarChart2 },
  { label: 'Review', href: '/review', icon: CheckSquare },
  { label: 'Evidence', href: '/evidence', icon: FolderOpen },
  { label: 'More', href: '#more', icon: MoreHorizontal },
]

function SidebarNavItem({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon
  return (
    <Link
      href={item.href}
      data-active={active ? 'true' : undefined}
      className={`
        flex items-center gap-3 px-4 py-2 rounded-sm font-ui text-sm font-medium transition-colors
        ${
          active
            ? 'border-l-2 border-accent bg-accent-soft text-accent'
            : 'text-text-muted hover:bg-accent-soft hover:text-text-body'
        }
      `}
    >
      <Icon size={16} className="shrink-0" />
      {item.label}
    </Link>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const { financialYear } = useWorkspaceStore()

  useAuth()

  return (
    <div className="flex min-h-screen bg-canvas">
      {/* ── Desktop sidebar ─────────────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 bg-surface border-r border-border">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-border">
          <span className="font-display text-xl font-semibold text-text-primary">
            Tax Return AI
          </span>
        </div>

        {/* FY switcher */}
        {financialYear && (
          <div className="px-4 py-3 border-b border-border">
            <button
              type="button"
              className="font-ui text-xs text-text-muted hover:text-text-body flex items-center gap-1"
            >
              FY {financialYear} ▾
            </button>
          </div>
        )}

        {/* Nav items */}
        <nav className="flex-1 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <SidebarNavItem
              key={item.href}
              item={item}
              active={pathname === item.href || pathname.startsWith(item.href + '?')}
            />
          ))}
        </nav>
      </aside>

      {/* ── Main content ─────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6">
          {children}
        </div>
      </main>

      {/* ── Mobile bottom tab bar ────────────────────────────────── */}
      <nav
        aria-label="Mobile navigation"
        className="md:hidden fixed bottom-0 inset-x-0 bg-surface border-t border-border flex"
      >
        {MOBILE_TABS.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href
          const tabClass = `flex-1 flex flex-col items-center justify-center py-2 gap-0.5 font-ui text-xs transition-colors ${
            active ? 'text-accent' : 'text-text-muted'
          }`
          if (item.href.startsWith('#')) {
            return (
              <button key={item.href} type="button" className={tabClass}>
                <Icon size={20} />
                {item.label}
              </button>
            )
          }
          return (
            <Link key={item.href} href={item.href} className={tabClass}>
              <Icon size={20} />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
