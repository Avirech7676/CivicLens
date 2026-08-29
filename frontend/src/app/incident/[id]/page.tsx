'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { 
  ShieldAlert, Sparkles, Building2, Wrench, AlertTriangle, 
  CheckCircle2, Clock, MapPin, ArrowRight, Layers, FileText, Flame, ExternalLink, Users
} from 'lucide-react';
import { getIncident, getIncidentHotspot } from '@/lib/api';
import { Incident, Hotspot } from '@/types';

function getCitizenStatusLabel(statusStr: string) {
  switch (statusStr) {
    case 'SUBMITTED':
      return { label: 'Report received', color: 'bg-sky-100 text-sky-800 border-sky-300' };
    case 'TRIAGED':
      return { label: 'Being reviewed', color: 'bg-indigo-100 text-indigo-800 border-indigo-300' };
    case 'ASSIGNED':
      return { label: 'Sent to department', color: 'bg-purple-100 text-purple-800 border-purple-300' };
    case 'IN_PROGRESS':
      return { label: 'Work in progress', color: 'bg-amber-100 text-amber-800 border-amber-300 animate-pulse' };
    case 'RESOLVED':
      return { label: 'Repair completed', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
    case 'VERIFIED':
      return { label: 'Fixed and confirmed', color: 'bg-emerald-600 text-white border-emerald-700' };
    default:
      return { label: 'Report received', color: 'bg-slate-100 text-slate-800 border-slate-300' };
  }
}

function getCitizenPriorityLabel(levelStr: string, score: number) {
  if (levelStr === 'P1_CRITICAL' || levelStr === 'P2_HIGH' || score >= 65) {
    return { label: 'High Priority', note: 'Prioritized because this may create a safety risk.' };
  } else if (levelStr === 'P3_MEDIUM' || score >= 45) {
    return { label: 'Medium Priority', note: 'Scheduled for standard maintenance response.' };
  } else {
    return { label: 'Normal Priority', note: 'Queued for routine municipal maintenance.' };
  }
}

export default function IncidentDetail() {
  const { id } = useParams();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [hotspot, setHotspot] = useState<Hotspot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      Promise.all([
        getIncident(id as string),
        getIncidentHotspot(id as string)
      ])
        .then(([incData, hsData]) => {
          setIncident(incData);
          setHotspot(hsData);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) {
    return (
      <div className="py-12 text-center text-slate-500 font-medium animate-pulse">
        Loading problem details and status update...
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-center">
        Unable to load report details: {error || 'Problem report not found'}
      </div>
    );
  }

  const statusBadge = getCitizenStatusLabel(incident.status);
  const priorityInfo = getCitizenPriorityLabel(incident.priority_level || 'P3', incident.priority_score || 50);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Title Header */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`px-3 py-1 text-xs font-bold rounded-full border ${statusBadge.color}`}>
              {statusBadge.label}
            </span>
            <span className="px-3 py-1 bg-slate-100 text-slate-700 border border-slate-200 font-medium text-xs rounded-full">
              {incident.category ? incident.category.replace('_', ' ') : 'Civic Issue'}
            </span>
            <span className="px-3 py-1 bg-amber-50 text-amber-900 border border-amber-200 text-xs font-bold rounded-full">
              {priorityInfo.label}
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900">{incident.title}</h1>
          <p className="text-xs text-slate-500 mt-1.5 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-slate-400" /> {incident.address || 'Location logged'} &bull; Reported {new Date(incident.created_at).toLocaleDateString()}
          </p>
        </div>

        {incident.status === 'RESOLVED' && (
          <Link
            href={`/verify/${incident.id}`}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm py-3 px-5 rounded-xl flex items-center gap-2 shadow-md transition shrink-0"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Verify Repair Fixed</span>
          </Link>
        )}
      </div>

      {/* PART OF CIVIC HOTSPOT BADGE CARD */}
      {hotspot && (
        <div className="bg-amber-950/90 border-2 border-amber-500 rounded-2xl p-5 text-white shadow-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 bg-amber-500 text-slate-950 font-bold rounded-xl shrink-0 mt-0.5">
              <Flame className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="px-2 py-0.5 bg-amber-500 text-slate-950 font-bold text-xs rounded uppercase">
                  Part of a Concentrated Problem Area
                </span>
              </div>
              <h3 className="text-base font-bold text-white">{hotspot.name}</h3>
              <p className="text-xs text-amber-200 mt-0.5">
                Several civic problems have been reported in this area. Local teams are aware of this pattern and working to address it.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Problem Reported & Evidence */}
        <div className="lg:col-span-2 space-y-6">
          {/* Problem Reported Section */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-sky-600" /> Problem Reported
            </h2>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-sm text-slate-800 leading-relaxed">
              "{incident.description}"
            </div>
          </div>

          {/* Other People Who Reported This (Duplicate Consolidation Presentation) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-600" /> Other People Who Reported This
              </h2>
              <span className="px-3 py-1 bg-indigo-50 text-indigo-800 border border-indigo-200 font-bold text-xs rounded-full">
                {incident.reports?.length || 1} {incident.reports?.length === 1 ? 'Citizen Report' : 'Citizen Reports Linked'}
              </span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Other citizens have reported the same issue nearby. Your report has been linked to this problem, helping local teams understand how widespread it is and prioritize repairs faster.
            </p>

            <div className="space-y-3 pt-2">
              {incident.reports && incident.reports.length > 0 ? (
                incident.reports.map((rep, idx) => (
                  <div key={rep.id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                    <div className="flex justify-between items-center text-slate-500 font-medium">
                      <span>Report #{idx + 1}</span>
                      <span>{new Date(rep.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-slate-800 italic">"{rep.description}"</p>
                    {rep.image_path && (
                      <div className="mt-2">
                        <img 
                          src={`http://localhost:8000/static/${rep.image_path.split('/').pop()}`} 
                          alt="Evidence photo" 
                          className="w-32 h-24 object-cover rounded-lg border border-slate-200 shadow-sm"
                        />
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-3.5 bg-slate-50 rounded-xl text-xs text-slate-600">
                  Your report is recorded as the primary report for this issue.
                </div>
              )}
            </div>
          </div>

          {/* What We Found Section */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" /> What We Found
            </h2>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="font-semibold text-slate-900">
                Safety Impact: <span className="font-bold text-amber-700">{incident.severity_level || 'MEDIUM'}</span>
              </div>
              {incident.severity_reason && (
                <p className="text-slate-600 italic">{incident.severity_reason}</p>
              )}
            </div>

            {incident.recommended_action && (
              <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-900 space-y-1">
                <span className="font-bold block">Recommended Repair Action:</span>
                <p>{incident.recommended_action}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Status, Department & Priorities */}
        <div className="space-y-6">
          {/* Who Is Handling It */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-indigo-600" /> Who Is Handling It
            </h2>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <span className="text-xs text-slate-500 font-medium block">Responsible Department</span>
              <span className="text-sm font-extrabold text-slate-900 block">
                {incident.assigned_department || 'Roads Department'}
              </span>
              <p className="text-xs text-slate-500 pt-1">
                Sent to the right department for inspection and work order scheduling.
              </p>
            </div>
          </div>

          {/* Priority Explanation */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-600" /> Priority Status
            </h2>

            <div className="p-4 bg-slate-900 text-white rounded-xl space-y-2 text-center">
              <span className="text-xs text-amber-400 font-bold uppercase tracking-wider block">
                {priorityInfo.label}
              </span>
              <p className="text-xs text-slate-300">{priorityInfo.note}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
