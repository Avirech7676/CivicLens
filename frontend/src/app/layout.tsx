import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/ui/Navigation';

export const metadata: Metadata = {
  title: 'CivicLens | AI Incident Resolution System',
  description: 'AI-powered civic incident classification, routing, and work order generation.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased">
        <Navigation />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="bg-slate-900 text-slate-400 py-6 text-center text-xs border-t border-slate-800">
          <div className="max-w-7xl mx-auto px-4">
            CivicLens Hackathon MVP &bull; BuildSprint 2026 &bull; AI-Powered Civic Incident Resolution
          </div>
        </footer>
      </body>
    </html>
  );
}
