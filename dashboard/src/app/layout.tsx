import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AutoForge — Autonomous AI Engineering Orchestrator',
  description: 'Real-time dashboard for AutoForge multi-agent DevOps intelligence',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
