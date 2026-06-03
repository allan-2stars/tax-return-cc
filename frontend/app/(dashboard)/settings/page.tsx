'use client'
import { useEffect, useState } from 'react'
import WorkspaceTab from '@/components/settings/WorkspaceTab'
import SecurityTab from '@/components/settings/SecurityTab'
import AiPrivacyTab from '@/components/settings/AiPrivacyTab'
import StorageTab from '@/components/settings/StorageTab'
import WorkspaceSafetyTab from '@/components/settings/WorkspaceSafetyTab'
import AboutTab from '@/components/settings/AboutTab'

type TabId = 'workspace' | 'security' | 'ai-privacy' | 'storage' | 'workspace-safety' | 'about'

const TABS: { id: TabId; label: string }[] = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'security', label: 'Security' },
  { id: 'ai-privacy', label: 'AI & Privacy' },
  { id: 'storage', label: 'Storage' },
  { id: 'workspace-safety', label: 'Workspace Safety' },
  { id: 'about', label: 'About' },
]

const SESSION_KEY = 'settings-active-tab'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('workspace')

  useEffect(() => {
    const saved = sessionStorage.getItem(SESSION_KEY) as TabId | null
    if (saved && TABS.some((t) => t.id === saved)) {
      setActiveTab(saved)
    }
  }, [])

  function switchTab(id: TabId) {
    setActiveTab(id)
    sessionStorage.setItem(SESSION_KEY, id)
  }

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-semibold text-text-primary">Settings</h1>

      <div
        role="tablist"
        className="flex gap-1 border-b border-border overflow-x-auto"
        aria-label="Settings tabs"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => switchTab(tab.id)}
            className={`px-4 py-2 text-sm font-ui font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-body'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="pt-2">
        {activeTab === 'workspace' && <WorkspaceTab />}
        {activeTab === 'security' && <SecurityTab />}
        {activeTab === 'ai-privacy' && <AiPrivacyTab />}
        {activeTab === 'storage' && <StorageTab />}
        {activeTab === 'workspace-safety' && <WorkspaceSafetyTab />}
        {activeTab === 'about' && <AboutTab />}
      </div>
    </div>
  )
}
