import type { Metadata } from 'next'
import './globals.css'

// Metadata da aplicação
export const metadata: Metadata = {
  title: 'Chat Lab-IA - SCoPE-AI',
  description: 'Interface de conversação com SCoPE-AI - Laboratório Lab-IA',
  icons: {
    icon: '/icon.ico',
  },
}

// Layout raiz da aplicação
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="icon" href="/icon.ico" sizes="any" />
      </head>
      <body className="min-h-screen bg-[#0f172a] text-[#f1f5f9]">
        {children}
      </body>
    </html>
  )
}
