'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck, User, Lock, ArrowRight, UserCheck, AlertCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('dispatcher@civiclens.local');
  const [password, setPassword] = useState('Dispatcher123!');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const userProfile = await login(email, password);
      if (userProfile.role === 'DISPATCHER') {
        router.push('/admin');
      } else if (userProfile.role === 'FIELD_CREW') {
        router.push('/crew');
      } else {
        router.push('/');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setSubmitting(false);
    }
  };

  const setDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="max-w-md mx-auto my-8 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm text-center space-y-2">
        <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white mx-auto shadow-md">
          <ShieldCheck className="w-7 h-7" />
        </div>
        <h1 className="text-2xl font-black text-slate-900">CivicLens</h1>
        <p className="text-xs text-slate-500 font-medium">Sign in to access operational role tools</p>
      </div>

      {/* Demo Selector Quick Fill Buttons */}
      <div className="bg-slate-900 text-white rounded-2xl p-5 border border-slate-800 space-y-3 shadow-md">
        <span className="text-[11px] font-mono text-indigo-300 font-bold uppercase tracking-wider block">
          Demo Accounts Available
        </span>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <button
            type="button"
            onClick={() => setDemoAccount('citizen@civiclens.local', 'Citizen123!')}
            className={`p-2.5 rounded-xl border text-center transition font-semibold ${
              email === 'citizen@civiclens.local'
                ? 'bg-indigo-600 border-indigo-400 text-white'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <div className="text-[10px] text-indigo-300 font-mono">CITIZEN</div>
            <div className="text-[11px] truncate mt-0.5">Citizen</div>
          </button>

          <button
            type="button"
            onClick={() => setDemoAccount('dispatcher@civiclens.local', 'Dispatcher123!')}
            className={`p-2.5 rounded-xl border text-center transition font-semibold ${
              email === 'dispatcher@civiclens.local'
                ? 'bg-indigo-600 border-indigo-400 text-white'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <div className="text-[10px] text-indigo-300 font-mono">DISPATCHER</div>
            <div className="text-[11px] truncate mt-0.5">Dispatcher</div>
          </button>

          <button
            type="button"
            onClick={() => setDemoAccount('crew@civiclens.local', 'Crew123!')}
            className={`p-2.5 rounded-xl border text-center transition font-semibold ${
              email === 'crew@civiclens.local'
                ? 'bg-indigo-600 border-indigo-400 text-white'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-800'
            }`}
          >
            <div className="text-[10px] text-indigo-300 font-mono">FIELD CREW</div>
            <div className="text-[11px] truncate mt-0.5">Field Crew</div>
          </button>
        </div>
      </div>

      {/* Login Form */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-indigo-600" /> Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-xl border border-slate-300 p-3 text-slate-900 outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-indigo-600" /> Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-xl border border-slate-300 p-3 text-slate-900 outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {submitting ? (
              <span>Signing In...</span>
            ) : (
              <>
                <span>Sign In to CivicLens</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
