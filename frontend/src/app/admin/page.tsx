'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  BarChart3, AlertOctagon, CheckCircle2, Clock, 
  MapPin, Eye, ShieldAlert, ArrowUpRight, Wrench, RefreshCw, 
  Building2, Flame, Layers, Sparkles, ChevronRight, X, Bot, Send, HelpCircle, ExternalLink
} from 'lucide-react';
import { 
  getIncidents, getStats, getWorkOrders, getHotspots, 
  updateIncidentStatus, updateWorkOrderStatus, queryAssistant 
} from '@/lib/api';
import { 
  Incident, DashboardStats, WorkOrder, Hotspot, 
  HotspotRecommendation, AssistantQueryResponse 
} from '@/types';
import LeafletMap from '@/components/ui/LeafletMap';

export default function AdminDashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [recommendations, setRecommendations] = useState<HotspotRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);

  // Command Assistant State
  const [assistantInput, setAssistantInput] = useState('');
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantResult, setAssistantResult] = useState<AssistantQueryResponse | null>(null);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [incData, woData, statsData, hsData] = await Promise.all([
        getIncidents(),
        getWorkOrders(),
        getStats(),
        getHotspots()
      ]);
      setIncidents(incData);
      setWorkOrders(woData);
      setStats(statsData);
      setHotspots(hsData.hotspots || []);
      setRecommendations(hsData.recommendations || []);
    } catch (err) {
      console.error('Failed to load admin data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleStartWork = async (incidentId: string) => {
    try {
      await updateIncidentStatus(incidentId, 'IN_PROGRESS', 'Work started by field crew.', 'DISPATCHER');
      await loadDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to start work');
    }
  };

  const handleCompleteWork = async (workOrderId: string) => {
    try {
      const formData = new FormData();
      formData.append('status', 'COMPLETED');
      formData.append('completion_notes', 'Field crew completed maintenance repairs.');
      await updateWorkOrderStatus(workOrderId, formData);
      await loadDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to complete work order');
    }
  };

  const handleAskAssistant = async (questionToAsk?: string) => {
    const q = (questionToAsk || assistantInput).trim();
    if (!q) return;

    setAssistantLoading(true);
    if (questionToAsk) setAssistantInput(questionToAsk);

    try {
      const res = await queryAssistant(q);
      setAssistantResult(res);
    } catch (err: any) {
      console.error('Failed to query assistant', err);
    } finally {
      setAssistantLoading(false);
    }
  };

  const suggestedQuestions = [
    "What should we fix first?",
    "Which areas need the most attention?",
    "Why was this problem given high priority?",
    "Which department has the most work?",
    "How many problems are waiting for verification?"
  ];

  const getHotspotLevelBadge = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 text-xs font-bold uppercase rounded bg-red-950 text-red-400 border border-red-800">Critical</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 text-xs font-bold uppercase rounded bg-orange-950 text-orange-400 border border-orange-800">High</span>;
      case 'EMERGING':
        return <span className="px-2 py-0.5 text-xs font-bold uppercase rounded bg-amber-950 text-amber-400 border border-amber-800">Emerging</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-bold uppercase rounded bg-slate-800 text-slate-300 border border-slate-700">Normal</span>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-sky-600" /> Dispatcher & Triage Command Center
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time incident management, spatial hotspot intelligence, and grounded AI Command Assistant.
          </p>
        </div>
        <button 
          onClick={loadDashboardData}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Dashboard
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 block">Total Reports</span>
          <span className="text-2xl font-black text-slate-900 mt-1 block">{stats?.total_reports ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 block">Unique Incidents</span>
          <span className="text-2xl font-black text-indigo-600 mt-1 block">{stats?.total_incidents ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 block">Detected Hotspots</span>
          <span className="text-2xl font-black text-amber-600 mt-1 block flex items-center gap-1">
            <Flame className="w-5 h-5 text-amber-500 inline" /> {hotspots.length}
          </span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 block">Resolved</span>
          <span className="text-2xl font-black text-emerald-600 mt-1 block">{stats?.resolved_incidents ?? 0}</span>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-medium text-slate-500 block">Citizen Verified</span>
          <span className="text-2xl font-black text-sky-600 mt-1 block">{stats?.verified_incidents ?? 0}</span>
        </div>
      </div>

      {/* CIVICLENS COMMAND ASSISTANT PANEL */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-indigo-600 rounded-lg text-white">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                CivicLens Command Assistant
              </h2>
              <p className="text-[11px] text-slate-400">
                Grounded Operational Intelligence &bull; Query active incidents, hotspots, priority reasoning & workloads
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
            Strict Data Grounding
          </span>
        </div>

        {/* Input Bar */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleAskAssistant(); }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={assistantInput}
              onChange={(e) => setAssistantInput(e.target.value)}
              placeholder='Ask CivicLens: "What should we fix first?" or "Where are the biggest hotspots?"'
              className="w-full bg-slate-950 border border-slate-700 text-white placeholder-slate-500 text-sm rounded-xl py-3 pl-4 pr-10 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            />
          </div>
          <button
            type="submit"
            disabled={assistantLoading || !assistantInput.trim()}
            className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 transition shrink-0 shadow"
          >
            {assistantLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>{assistantLoading ? 'Analyzing...' : 'Ask CivicLens'}</span>
          </button>
        </form>

        {/* Suggested Question Chips */}
        <div className="flex items-center gap-2 flex-wrap text-xs pt-1">
          <span className="text-slate-400 text-[11px] font-medium flex items-center gap-1">
            <HelpCircle className="w-3.5 h-3.5 text-slate-500" /> Suggested Questions:
          </span>
          {suggestedQuestions.map((qText, i) => (
            <button
              key={`sq-${i}`}
              onClick={() => handleAskAssistant(qText)}
              className="px-2.5 py-1 bg-slate-800 hover:bg-indigo-950 hover:text-indigo-300 text-slate-300 text-[11px] rounded-lg border border-slate-700 transition"
            >
              "{qText}"
            </button>
          ))}
        </div>

        {/* Assistant Response Output Box */}
        {assistantResult && (
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4 text-xs mt-3 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
              <span className="font-semibold text-slate-300">
                Q: "{assistantResult.question}"
              </span>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                Intent: {assistantResult.intent}
              </span>
            </div>

            <div className="text-slate-200 whitespace-pre-wrap leading-relaxed font-sans text-sm">
              {assistantResult.answer}
            </div>

            {/* Factual Source Links */}
            {assistantResult.sources && assistantResult.sources.length > 0 && (
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  Based On CivicLens Operational Records:
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  {assistantResult.sources.map((src, idx) => {
                    if (src.type === 'incident') {
                      return (
                        <Link
                          key={`src-${idx}`}
                          href={`/incident/${src.id}`}
                          className="px-2.5 py-1 bg-indigo-950 hover:bg-indigo-900 border border-indigo-700 text-indigo-300 rounded-lg font-medium flex items-center gap-1 text-[11px] transition"
                        >
                          <span>Incident: {src.label}</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      );
                    } else if (src.type === 'hotspot') {
                      return (
                        <button
                          key={`src-${idx}`}
                          onClick={() => {
                            const hs = hotspots.find(h => h.hotspot_id === src.id);
                            if (hs) setSelectedHotspot(hs);
                          }}
                          className="px-2.5 py-1 bg-amber-950 hover:bg-amber-900 border border-amber-700 text-amber-300 rounded-lg font-medium flex items-center gap-1 text-[11px] transition"
                        >
                          <span>{src.label}</span>
                          <Flame className="w-3 h-3 text-amber-400" />
                        </button>
                      );
                    } else {
                      return (
                        <span
                          key={`src-${idx}`}
                          className="px-2.5 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg font-medium text-[11px]"
                        >
                          {src.label}
                        </span>
                      );
                    }
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* "WHAT SHOULD WE FIX FIRST?" (CivicLens Recommends) */}
      {recommendations.length > 0 && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              <h2 className="text-base font-bold text-slate-900">
                WHAT SHOULD WE FIX FIRST? (CivicLens Recommends)
              </h2>
            </div>
            <span className="text-xs text-slate-500 font-mono">Deterministic Ranking Engine</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {recommendations.map((rec, idx) => (
              <div
                key={`rec-${idx}`}
                className={`p-4 rounded-xl border text-xs space-y-2 relative transition ${
                  rec.type === 'HOTSPOT'
                    ? 'bg-red-50/60 border-red-200 hover:bg-red-50'
                    : 'bg-slate-50/80 border-slate-200 hover:bg-slate-100/80'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-0.5 font-bold rounded uppercase text-[10px] ${
                    rec.type === 'HOTSPOT' ? 'bg-red-600 text-white' : 'bg-indigo-600 text-white'
                  }`}>
                    {rec.type === 'HOTSPOT' ? 'CRITICAL HOTSPOT' : (rec.priority_level || 'P1')}
                  </span>
                  <span className="font-mono font-bold text-slate-700">
                    {rec.score} / 100
                  </span>
                </div>

                <h3 className="font-bold text-sm text-slate-900 line-clamp-1">{rec.title}</h3>
                <p className="text-slate-600 leading-relaxed line-clamp-2">{rec.reason}</p>

                {rec.hotspot_id && (
                  <button
                    onClick={() => {
                      const hs = hotspots.find(h => h.hotspot_id === rec.hotspot_id);
                      if (hs) setSelectedHotspot(hs);
                    }}
                    className="text-amber-600 hover:text-amber-700 font-semibold flex items-center gap-1 text-[11px] pt-1"
                  >
                    <span>Inspect Hotspot &rarr;</span>
                  </button>
                )}

                {rec.incident_id && (
                  <Link
                    href={`/incident/${rec.incident_id}`}
                    className="text-sky-600 hover:text-sky-700 font-semibold flex items-center gap-1 text-[11px] pt-1"
                  >
                    <span>View Incident &rarr;</span>
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Content Area - Incidents, Hotspots & Map Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Triage Queue & Hotspots List (2 Cols) */}
        <div className="lg:col-span-2 space-y-8">
          {/* Spatial Hotspots Section */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-amber-500" />
                <h2 className="text-base font-bold text-slate-900">Detected Spatial Civic Hotspots</h2>
              </div>
              <span className="text-xs text-slate-500 font-mono">{hotspots.length} Concentrated Patterns</span>
            </div>

            {hotspots.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">No spatial hotspots detected across current active incidents.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {hotspots.map((hs) => (
                  <div
                    key={hs.hotspot_id}
                    onClick={() => setSelectedHotspot(hs)}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-100/80 transition cursor-pointer space-y-2 border-l-4 border-l-amber-500 shadow-sm group"
                  >
                    <div className="flex items-center justify-between">
                      {getHotspotLevelBadge(hs.hotspot_level)}
                      <span className="text-xs font-mono font-black text-slate-700">
                        Score: {hs.hotspot_score}/100
                      </span>
                    </div>

                    <h3 className="font-bold text-sm text-slate-900 group-hover:text-sky-600 transition">
                      {hs.name}
                    </h3>

                    <div className="flex items-center gap-3 text-xs text-slate-600 flex-wrap">
                      <span><strong>{hs.incident_count}</strong> Incidents</span>
                      <span>&bull;</span>
                      <span><strong>{hs.report_count}</strong> Reports</span>
                      <span>&bull;</span>
                      <span className="font-semibold text-slate-700">Pattern: {hs.pattern}</span>
                    </div>

                    <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed italic">
                      "{hs.explanation}"
                    </p>

                    <div className="text-[11px] font-semibold text-sky-600 flex items-center justify-end gap-0.5 pt-1">
                      <span>Inspect Drill-Down</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Incident Triage Queue */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 font-semibold text-slate-800 text-sm flex justify-between items-center">
              <span>Canonical Incident Triage Queue</span>
              <span className="text-xs font-normal text-slate-500">{incidents.length} Records</span>
            </div>

            {loading ? (
              <div className="p-8 text-center text-slate-500 text-sm">Loading queue...</div>
            ) : incidents.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">No incidents submitted yet.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {incidents.map((inc) => (
                  <div key={inc.id} className="p-5 hover:bg-slate-50 transition flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold font-mono text-slate-600">
                          INC-{inc.id.slice(0, 6).toUpperCase()}
                        </span>
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded">
                          {inc.severity_level}
                        </span>
                        <span className="px-2 py-0.5 bg-indigo-600 text-white text-[10px] font-bold rounded">
                          {inc.priority_level || 'P3'} ({inc.priority_score}/100)
                        </span>
                        <span className="px-2 py-0.5 bg-sky-100 text-sky-800 text-[10px] font-bold rounded flex items-center gap-1">
                          {inc.reports?.length || 1} {inc.reports?.length === 1 ? 'Report' : 'Reports'}
                        </span>
                        <span className="text-xs text-slate-400">&bull; {inc.status}</span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">{inc.title}</h3>
                      <p className="text-xs text-slate-500 flex items-center gap-1">
                        <MapPin className="w-3 h-3" /> {inc.address || 'Location logged'} &bull; <Building2 className="w-3 h-3 text-indigo-500" /> <span className="font-semibold text-slate-700">{inc.assigned_department || 'Department unassigned'}</span>
                      </p>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-auto">
                      {inc.status === 'SUBMITTED' || inc.status === 'TRIAGED' || inc.status === 'ASSIGNED' ? (
                        <button
                          onClick={() => handleStartWork(inc.id)}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow transition"
                        >
                          Start Work
                        </button>
                      ) : null}

                      <Link
                        href={`/incident/${inc.id}`}
                        className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium flex items-center gap-1 transition"
                      >
                        <span>Review</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Interactive Map & Work Orders */}
        <div className="space-y-6">
          {/* Interactive Leaflet Command Center Map */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
            <span className="text-xs font-semibold text-slate-700 block flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-sky-600" /> Spatial Intelligence Map Layer
            </span>
            <LeafletMap
              incidents={incidents}
              hotspots={hotspots}
              selectedHotspotId={selectedHotspot?.hotspot_id}
              onSelectHotspot={(hs) => setSelectedHotspot(hs)}
              className="h-80 w-full rounded-xl overflow-hidden border border-slate-200 shadow-inner"
            />
          </div>

          {/* Active Work Orders List */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
            <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
              <Wrench className="w-4 h-4 text-indigo-600" /> Active Work Orders ({workOrders.length})
            </span>
            <div className="space-y-2">
              {workOrders.map((wo) => (
                <div key={wo.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-800">{wo.assigned_department}</span>
                    <span className="text-[10px] text-indigo-600 font-bold uppercase">{wo.status}</span>
                  </div>
                  <div className="text-slate-600 truncate">{wo.recommended_action}</div>
                  {wo.status !== 'COMPLETED' && (
                    <button
                      onClick={() => handleCompleteWork(wo.id)}
                      className="w-full py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] rounded transition"
                    >
                      Mark Resolved ✓
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Hotspot Drill-Down Modal Drawer */}
      {selectedHotspot && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full p-6 space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {getHotspotLevelBadge(selectedHotspot.hotspot_level)}
                  <span className="text-xs font-mono font-bold text-slate-500">
                    HOTSPOT #{selectedHotspot.hotspot_id.toUpperCase()} &bull; SCORE {selectedHotspot.hotspot_score}/100
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900">{selectedHotspot.name}</h2>
              </div>
              <button
                onClick={() => setSelectedHotspot(null)}
                className="p-2 text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 leading-relaxed">
              <strong className="font-bold block mb-0.5">Spatial Pattern Explanation:</strong>
              {selectedHotspot.explanation}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Incidents</span>
                <span className="text-lg font-bold text-slate-900">{selectedHotspot.incident_count}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Citizen Reports</span>
                <span className="text-lg font-bold text-slate-900">{selectedHotspot.report_count}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Average Priority</span>
                <span className="text-lg font-bold text-indigo-600">{selectedHotspot.average_priority_score}/100</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-slate-500 block">Dominant Category</span>
                <span className="text-xs font-bold text-slate-800 truncate block mt-1">{selectedHotspot.dominant_category.replace('_', ' ')}</span>
              </div>
            </div>

            {/* Affected Incidents List */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Concentrated Incidents in Hotspot Cluster ({selectedHotspot.incident_ids.length})
              </h3>
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
                {incidents.filter(inc => selectedHotspot.incident_ids.includes(inc.id)).map(inc => (
                  <div key={`hs-inc-${inc.id}`} className="p-3.5 hover:bg-slate-50 transition flex items-center justify-between text-xs">
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-mono font-bold text-slate-600">INC-{inc.id.slice(0, 6)}</span>
                        <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-800 font-bold rounded text-[10px]">{inc.priority_level} ({inc.priority_score})</span>
                        <span className="text-slate-400">&bull; {inc.status}</span>
                      </div>
                      <div className="font-bold text-slate-900">{inc.title}</div>
                      <div className="text-[11px] text-slate-500">{inc.assigned_department || 'Unassigned'}</div>
                    </div>

                    <Link
                      href={`/incident/${inc.id}`}
                      className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-white rounded font-medium text-[11px] shrink-0"
                    >
                      View
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
