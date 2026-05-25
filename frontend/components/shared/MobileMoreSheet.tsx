'use client'
import React from 'react'
import Link from 'next/link'

interface SheetItem {
  href: string
  label: string
  icon: React.ComponentType<{ size?: number | string; className?: string }>
}

interface MobileMoreSheetProps {
  onClose: () => void
  items: SheetItem[]
}

export default function MobileMoreSheet({ onClose, items }: MobileMoreSheetProps) {
  return (
    <>
      <div
        aria-hidden="true"
        data-testid="more-sheet-backdrop"
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="More options"
        className="fixed inset-x-0 bottom-0 z-50 bg-surface border-t border-border rounded-t-2xl shadow-xl"
        style={{ transform: 'translateY(0)', transition: 'transform 200ms ease-out' }}
      >
        <div aria-hidden="true" className="w-12 h-1 bg-border rounded-full mx-auto mt-3 mb-2" />
        <nav aria-label="More navigation">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className="flex items-center gap-4 px-6 py-4 font-ui text-sm text-text-body border-b border-border hover:bg-accent-soft"
            >
              <Icon size={20} className="text-text-muted shrink-0" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </>
  )
}
