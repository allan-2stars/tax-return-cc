import type { Metadata } from 'next'
import Providers from '@/components/shared/Providers'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: 'Tax Return AI',
  description: 'AI-guided tax preparation workspace for Australian taxpayers',
  manifest: '/manifest.json',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="font-body">
      <body className="bg-canvas text-text-body min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
