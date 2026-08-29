import React from 'react';
import Link from 'next/link';
import { Camera, ShieldAlert, CheckCircle, BarChart3, MapPin } from 'lucide-react';
import NotificationCenter from './NotificationCenter';

export default function Navigation() {
  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2 text-xl font-bold tracking-tight text-white hover:text-sky-400 transition">
            <div className="p-1.5 bg-sky-600 rounded-lg text-white">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <span>CivicLens</span>
            <span className="text-xs px-2 py-0.5 bg-sky-950 text-sky-400 border border-sky-800 rounded-full font-mono font-normal ml-1">
              BuildSprint '26
            </span>
          </Link>

          <nav className="flex items-center gap-1 sm:gap-4 text-sm font-medium">
            <Link 
              href="/" 
              className="px-3 py-2 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition flex items-center gap-1.5"
            >
              <Camera className="w-4 h-4 text-sky-400" />
              <span>Report a Problem</span>
            </Link>
            
            <Link 
              href="/admin" 
              className="px-3 py-2 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition flex items-center gap-1.5"
            >
              <BarChart3 className="w-4 h-4 text-indigo-400" />
              <span>Dispatcher Portal</span>
            </Link>

            <NotificationCenter />
          </nav>
        </div>
      </div>
    </header>
  );
}
