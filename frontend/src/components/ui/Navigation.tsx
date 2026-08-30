'use client';

import React from 'react';
import Link from 'next/link';
import { Camera, ShieldAlert, CheckCircle, BarChart3, Wrench, User, LogOut, LogIn } from 'lucide-react';
import NotificationCenter from './NotificationCenter';
import { useAuth } from '@/context/AuthContext';

export default function Navigation() {
  const { user, logout, isDispatcher, isFieldCrew } = useAuth();

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

          <nav className="flex items-center gap-1 sm:gap-3 text-xs sm:text-sm font-medium">
            <Link 
              href="/" 
              className="px-3 py-2 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition flex items-center gap-1.5"
            >
              <Camera className="w-4 h-4 text-sky-400" />
              <span className="hidden sm:inline">Report Issue</span>
            </Link>

            {isDispatcher && (
              <Link 
                href="/admin" 
                className="px-3 py-2 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition flex items-center gap-1.5"
              >
                <BarChart3 className="w-4 h-4 text-indigo-400" />
                <span>Dispatcher Admin</span>
              </Link>
            )}

            {isFieldCrew && (
              <Link 
                href="/crew" 
                className="px-3 py-2 rounded-md hover:bg-slate-800 text-slate-300 hover:text-white transition flex items-center gap-1.5"
              >
                <Wrench className="w-4 h-4 text-emerald-400" />
                <span>Field Crew</span>
              </Link>
            )}

            <NotificationCenter />

            {/* Auth Profile / Role Badge */}
            {user ? (
              <div className="flex items-center gap-2 border-l border-slate-800 pl-3 ml-1">
                <span className="px-2 py-0.5 bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono font-bold text-[10px] rounded uppercase">
                  {user.role}
                </span>
                <button
                  onClick={logout}
                  title="Sign Out"
                  className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow transition flex items-center gap-1 ml-1"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Link>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}
