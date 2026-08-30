'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Sparkles, CheckCircle2, ChevronRight, User, ShieldAlert, Wrench, BarChart3, HelpCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function GoldenPathDemoBanner() {
  const { user, isCitizen, isDispatcher, isFieldCrew } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="bg-slate-900 text-white border-b border-slate-800 text-xs py-2 px-4">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-mono">
          <span className="px-2 py-0.5 bg-indigo-600 text-white font-bold rounded text-[10px] uppercase flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> DEMO GUIDE
          </span>
          <span className="text-slate-300">Active Role:</span>
          <span className="font-bold text-sky-400 uppercase">
            {user ? `${user.role} (${user.email})` : 'UNAUTHENTICATED (CITIZEN MODE)'}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap text-[11px]">
          <span className="text-slate-400 hidden lg:inline">Golden Path:</span>
          <span className={`px-2 py-0.5 rounded font-semibold ${isCitizen ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
            1. Report (Citizen)
          </span>
          <ChevronRight className="w-3 h-3 text-slate-600 hidden sm:inline" />
          <span className={`px-2 py-0.5 rounded font-semibold ${isDispatcher ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
            2. Assign Crew (Dispatcher)
          </span>
          <ChevronRight className="w-3 h-3 text-slate-600 hidden sm:inline" />
          <span className={`px-2 py-0.5 rounded font-semibold ${isFieldCrew ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
            3. Repair & Complete (Crew)
          </span>
          <ChevronRight className="w-3 h-3 text-slate-600 hidden sm:inline" />
          <span className={`px-2 py-0.5 rounded font-semibold ${isCitizen ? 'bg-amber-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
            4. Verify / Reopen (Citizen)
          </span>

          <Link href="/login" className="ml-2 text-indigo-300 hover:text-white underline font-semibold">
            Switch Role
          </Link>
        </div>
      </div>
    </div>
  );
}
