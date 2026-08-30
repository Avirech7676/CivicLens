'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { 
  ShieldAlert, Sparkles, Building2, Wrench, AlertTriangle, 
  CheckCircle2, Clock, MapPin, ArrowRight, Layers, FileText, Flame, ExternalLink 
} from 'lucide-react';
import { getIncident, getIncidentHotspot, getMediaUrl } from '@/lib/api';
import { Incident, Hotspot } from '@/types';

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
        Loading incident details & AI reasoning logs...
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-center">
        Failed to load incident record: {error || 'Incident not found'}
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Title Header */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-1 bg-slate-100 text-slate-700 border border-slate-300 font-mono text-xs rounded-md">
              INCIDENT-{incident.id.slice(0, 8).toUpperCase()}
            </span>
            <span className="px-2.5 py-1 bg-sky-100 text-sky-800 font-medium text-xs rounded-md">
              {incident.category || 'General'}
            </span>
            <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 font-semibold text-xs rounded-md">
              {incident.status}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">{incident.title}</h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5" /> {incident.address || 'Address unassigned'} &bull; Submitted {new Date(incident.created_at).toLocaleString()}
          </p>
        </div>

        <Link
          href={`/verify/${incident.id}`}
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm py-2.5 px-4 rounded-xl flex items-center gap-1.5 shadow transition"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>Verify Resolution</span>
        </Link>
      </div>

      {/* PART OF CIVIC HOTSPOT BADGE CARD */}
      {hotspot && (
        <div className="bg-amber-950/90 border-2 border-amber-500 rounded-2xl p-5 text-white shadow-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 bg-amber-500 text-slate-950 font-bold rounded-xl shrink-0">
              <Flame className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="px-2 py-0.5 bg-amber-500 text-slate-950 font-mono font-bold text-xs rounded uppercase">
                  PART OF CIVIC HOTSPOT
                </span>
                <span className="text-xs font-mono text-amber-300">
                  {hotspot.hotspot_level} LEVEL &bull; SCORE {hotspot.hotspot_score}/100
                </span>
              </div>
              <h3 className="text-base font-bold text-white">{hotspot.name}</h3>
              <p className="text-xs text-amber-200 mt-0.5">
                {hotspot.incident_count} Concentrated Incidents &bull; {hotspot.report_count} Total Reports &bull; Pattern: {hotspot.pattern}
              </p>
            </div>
          </div>

          <Link
            href="/admin"
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition shrink-0 flex items-center gap-1 shadow"
          >
            <span>View Hotspot Command Center</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Detailed Breakdown */}
        <div className="lg:col-span-2 space-y-6">
          {/* Complaint & Evidence Card */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-600" /> Citizen Reports & Aggregation
              </h2>
              <span className="px-3 py-1 bg-sky-50 text-sky-700 border border-sky-200 font-bold text-xs rounded-full flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-sky-600" />
                {incident.reports?.length || 1} {incident.reports?.length === 1 ? 'Report' : 'Reports Aggregated'}
              </span>
            </div>

            {/* List of aggregated reports */}
            <div className="space-y-3">
              {incident.reports && incident.reports.length > 0 ? (
                incident.reports.map((rep, idx) => (
                  <div key={rep.id} className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                    <div className="flex justify-between items-center text-xs font-mono text-slate-500">
                      <span className="font-semibold text-slate-700">Submission #{idx + 1} ({rep.id.slice(0, 8).toUpperCase()})</span>
                      <span>{new Date(rep.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-sm text-slate-700 leading-relaxed">
                      "{rep.description}"
                    </p>
                    {rep.image_path && (
                      <div className="mt-2">
                        <img 
                          src={getMediaUrl(rep.image_path)} 
                          alt="Citizen evidence photo" 
                          className="w-32 h-24 object-cover rounded-lg border border-slate-200 shadow-sm"
                        />
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-4 text-xs text-slate-500 bg-slate-50 rounded-lg">No reports attached.</div>
              )}
            </div>
          </div>

          {/* Actionable WorkOrder Card */}
            {incident.work_order && (
              <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
                <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                  <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-indigo-600" /> Actionable Field WorkOrder
                  </h2>
                  <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 font-mono font-bold text-xs rounded-md uppercase border border-indigo-200">
                    {incident.work_order.status}
                  </span>
                </div>

                <div className="space-y-3 text-xs text-slate-700">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="font-semibold text-slate-900 block">Recommended Field Procedure</span>
                    <p>{incident.work_order.recommended_action}</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                      <span className="font-semibold text-slate-900 block">Required Tools & Materials</span>
                      <p>{incident.work_order.required_materials || 'Standard maintenance kit'}</p>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                      <span className="font-semibold text-slate-900 block">Safety & PPE Guidelines</span>
                      <p>{incident.work_order.safety_precautions || 'High-vis vests & safety cones'}</p>
                    </div>
                  </div>

                  {/* Completion Evidence (if completed / resolved) */}
                  {incident.work_order.completion_notes && (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2 mt-3">
                      <span className="font-bold text-emerald-900 flex items-center gap-1.5 text-xs">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Municipal Resolution Evidence
                      </span>
                      <p className="text-emerald-800 text-xs">{incident.work_order.completion_notes}</p>
                      {incident.work_order.completion_image_path && (
                        <div className="mt-2">
                          <img
                            src={getMediaUrl(incident.work_order.completion_image_path)}
                            alt="Completion Evidence"
                            className="w-48 h-36 object-cover rounded-lg border border-emerald-300 shadow-sm"
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

          {/* AI Multimodal Analysis Logs */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" /> AI Engine Multimodal Analysis
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                <span className="text-slate-500 font-medium block">Severity Level</span>
                <span className="text-sm font-bold text-slate-800">{incident.severity_level || 'MEDIUM'}</span>
                {incident.severity_reason && (
                  <p className="text-[11px] text-slate-500 italic mt-1">{incident.severity_reason}</p>
                )}
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                <span className="text-slate-500 font-medium block">AI Vision Confidence</span>
                <span className="text-sm font-bold text-sky-600">
                  {incident.confidence ? `${Math.round(incident.confidence * 100)}%` : 'N/A'}
                </span>
              </div>
            </div>

            {incident.recommended_action && (
              <div className="p-4 bg-sky-50 rounded-lg border border-sky-200 text-xs text-sky-900 space-y-1">
                <span className="font-bold block">AI Recommended Operational Action:</span>
                <p>{incident.recommended_action}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Priority & Department Routing */}
        <div className="space-y-6">
          {/* Deterministic Priority Score Card */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-indigo-600" /> Priority Engine Evaluation
            </h2>

            <div className="p-4 bg-indigo-950 text-white rounded-xl space-y-2 text-center">
              <span className="text-xs text-indigo-300 font-mono uppercase block">Priority Level</span>
              <span className="text-2xl font-black text-amber-400 block">{incident.priority_level || 'P3_MEDIUM'}</span>
              <div className="text-3xl font-black text-white">
                {incident.priority_score} <span className="text-xs text-indigo-300 font-normal">/ 100</span>
              </div>
            </div>

            {incident.priority_reason && (
              <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200 italic">
                "{incident.priority_reason}"
              </div>
            )}
          </div>

          {/* Department Routing Card */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-indigo-600" /> Department Routing
            </h2>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <span className="text-xs text-slate-500 font-medium block">Assigned Municipal Dept</span>
              <span className="text-sm font-bold text-slate-900 block">{incident.assigned_department || 'Unassigned'}</span>
              {incident.routing_reason && (
                <p className="text-xs text-slate-500 italic border-t border-slate-200 pt-2 mt-2">
                  {incident.routing_reason}
                </p>
              )}
            </div>
          </div>
          {/* Incident Audit Timeline Card */}
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-600" /> Operational Incident Audit Timeline
            </h2>

            {incident.verification_notes && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg text-xs space-y-1 mb-2">
                <span className="font-bold block">Citizen Resolution Feedback:</span>
                <p>"{incident.verification_notes}"</p>
              </div>
            )}

            {incident.status_logs && incident.status_logs.length > 0 ? (
              <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-200">
                {incident.status_logs.map((log) => (
                  <div key={log.id} className="relative pl-8 text-xs space-y-1">
                    <div className="absolute left-1.5 top-1 w-4 h-4 rounded-full bg-indigo-600 border-2 border-white shadow-sm flex items-center justify-center">
                      <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                    </div>
                    <div className="flex justify-between items-center text-slate-500 font-mono text-[11px]">
                      <span className="font-bold text-slate-800 uppercase">{log.new_status}</span>
                      <span>{new Date(log.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="text-slate-600">
                      Changed by <span className="font-bold text-slate-800">{log.changed_by}</span>
                      {log.old_status && <span> from <span className="font-semibold text-slate-700">{log.old_status}</span></span>}
                    </div>
                    {log.notes && (
                      <p className="text-slate-500 italic bg-slate-50 p-2 rounded border border-slate-100 mt-1">"{log.notes}"</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-500 text-center">No lifecycle transition logs recorded yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
