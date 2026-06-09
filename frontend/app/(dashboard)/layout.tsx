// frontend/app/(dashboard)/layout.tsx
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Map,
  BarChart2,
  SearchX,
  FolderOpen,
  CheckSquare,
  Package,
  Settings,
  MoreHorizontal,
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import useWorkspaceStore from '@/lib/stores/workspace.store'
import NewFYModal from '@/components/settings/NewFYModal'
import DeadlineBanner from '@/components/shared/DeadlineBanner'
import NetworkBanner from '@/components/shared/NetworkBanner'
import MobileMoreSheet from '@/components/shared/MobileMoreSheet'
import { listWorkspaces, selectWorkspace } from '@/lib/api/settings'
import type { CreateWorkspaceResult, WorkspaceInfo } from '@/lib/api/types'

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ size?: number | string; className?: string }>
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Tax Journey', href: '/journey', icon: Map },
  { label: 'Tax Readiness', href: '/readiness', icon: BarChart2 },
  { label: 'Missing Evidence', href: '/readiness/missing', icon: SearchX },
  { label: 'Supporting Evidence', href: '/evidence', icon: FolderOpen },
  { label: 'Review', href: '/review', icon: CheckSquare },
  { label: 'Export Review Pack', href: '/export', icon: Package },
  { label: 'Settings', href: '/settings', icon: Settings },
]

const MORE_SHEET_ITEMS: NavItem[] = [
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
  const router = useRouter()
  const { financialYear, setWorkspace } = useWorkspaceStore()
  const [showNewFY, setShowNewFY] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [fyMenuOpen, setFyMenuOpen] = useState(false)
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([])

  const { isAuthenticated, sessionRestored, clearSessionRestored } = useAuth()

  useEffect(() => {
    let cancelled = false
    if (!isAuthenticated) return

    listWorkspaces()
      .then((res) => {
        if (!cancelled) {
          setWorkspaces(res.data.data.items)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setWorkspaces([])
        }
      })

    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
        <p className="text-sm font-ui text-text-muted">Loading…</p>
      </div>
    )
  }

  function handleNewFYSuccess(ws: CreateWorkspaceResult) {
    setWorkspace(ws.id, ws.financial_year)
    setShowNewFY(false)
    router.push('/journey')
  }

  async function handleSelectWorkspace(ws: WorkspaceInfo) {
    await selectWorkspace(ws.id)
    setWorkspace(ws.id, ws.financial_year)
    setFyMenuOpen(false)
    router.push('/journey')
    router.refresh()
  }

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
          <div className="px-4 py-3 border-b border-border relative">
            <button
              type="button"
              className="font-ui text-xs text-text-muted hover:text-text-body flex items-center gap-1"
              onClick={() => setFyMenuOpen((open) => !open)}
            >
              FY {financialYear} ▾
            </button>
            {fyMenuOpen && (
              <div className="mt-3 rounded-md border border-border bg-surface shadow-md p-2 space-y-1">
                <p className="px-2 py-1 text-xs font-ui text-text-muted">Tax years</p>
                {workspaces.map((ws) => {
                  const isCurrent = ws.financial_year === financialYear
                  return (
                    <button
                      key={ws.id}
                      type="button"
                      onClick={() => handleSelectWorkspace(ws)}
                      className={`w-full rounded-sm px-2 py-2 text-left text-sm font-ui transition-colors ${
                        isCurrent
                          ? 'bg-accent-soft text-accent'
                          : 'text-text-body hover:bg-surface-raised'
                      }`}
                    >
                      <span>{ws.financial_year}</span>
                      {isCurrent && <span className="ml-2 text-xs">Current</span>}
                    </button>
                  )
                })}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setFyMenuOpen(false)
                      setShowNewFY(true)
                    }}
                    className="w-full rounded-sm px-2 py-2 text-left text-sm font-ui text-accent hover:bg-surface-raised"
                  >
                    Start new tax year return
                  </button>
                </div>
              </div>
            )}
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
          <div className="mx-3 mt-4 rounded-md border border-border bg-surface-raised px-3 py-3">
            <p className="text-xs font-ui font-semibold text-text-primary">Suggested order</p>
            <p className="mt-1 text-xs font-ui text-text-muted">
              Journey → Evidence → Review → Readiness → Export
            </p>
          </div>
        </nav>
      </aside>

      {/* ── Main content ─────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        <NetworkBanner />
        {sessionRestored && (
          <div className="bg-ready-bg border-b border-ready px-4 py-2 flex items-center justify-between gap-3">
            <p className="text-sm font-ui text-ready">
              Session restored. Your workspace data is up to date.
            </p>
            <button
              type="button"
              onClick={clearSessionRestored}
              aria-label="Dismiss session restored message"
              className="text-sm font-ui text-ready underline"
            >
              Dismiss
            </button>
          </div>
        )}
        <DeadlineBanner />
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
              <button
                key={item.href}
                type="button"
                className={tabClass}
                onClick={() => setMoreOpen(true)}
              >
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

      {moreOpen && (
        <MobileMoreSheet
          onClose={() => setMoreOpen(false)}
          items={MORE_SHEET_ITEMS}
        />
      )}

      {showNewFY && financialYear && (
        <NewFYModal
          currentFY={financialYear}
          onSuccess={handleNewFYSuccess}
          onCancel={() => setShowNewFY(false)}
        />
      )}
    </div>
  )
}
