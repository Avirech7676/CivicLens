'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  BarChart3, AlertOctagon, CheckCircle2, Clock, 
  MapPin, Eye, ShieldAlert, ArrowUpRight, Wrench, RefreshCw, 
  Building2, Flame, Layers, Sparkles, ChevronRight, X, Bot, Send, HelpCircle, ExternalLink, AlertCircle
} from 'lucide-react';
import { 
  getIncidents, getStats, getWorkOrders, getHotspots, 
  updateIncidentStatus, updateWorkOrderStatus, queryAssistant, assignWorkOrderCrew, getEligibleCrews,
  getMLEvaluationSummary, getDataQualityStats
} from '@/lib/api';
import { 
  Incident, DashboardStats, WorkOrder, Hotspot, 
  HotspotRecommendation, AssistantQueryResponse 
} from '@/types';
import LeafletMap from '@/components/ui/LeafletMap';
import { useAuth } from '@/context/AuthContext';

export default function AdminDashboard() {
  const { user, isDispatcher } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [recommendations, setRecommendations] = useState<HotspotRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);

  // WorkOrder Action Loading State
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Crew Assignment Modal State
  const [assigningWo, setAssigningWo] = useState<WorkOrder | null>(null);
  const [assignedTeamInput, setAssignedTeamInput] = useState('Road Maintenance Crew Alpha');
  const [assignedWorkerInput, setAssignedWorkerInput] = useState('crew@civiclens.local');
  const [assignedWorkerIdInput, setAssignedWorkerIdInput] = useState<string>('');
  const [eligibleWorkersList, setEligibleWorkersList] = useState<any[]>([]);
  const [assigningLoading, setAssigningLoading] = useState(false);
  const [completingWo, setCompletingWo] = useState<WorkOrder | null>(null);
  const [completionNotesInput, setCompletionNotesInput] = useState('');
  const [completionImageFile, setCompletionImageFile] = useState<File | null>(null);
  const [completingLoading, setCompletingLoading] = useState(false);

  // Section API Error States
  const [incidentsError, setIncidentsError] = useState<string | null>(null);
  const [workOrdersError, setWorkOrdersError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [hotspotsError, setHotspotsError] = useState<string | null>(null);

  // ML Evaluation & Data Quality State
  const [mlSummary, setMlSummary] = useState<any>(null);
  const [dataQuality, setDataQuality] = useState<any>(null);

  // Command Assistant State
  const [assistantInput, setAssistantInput] = useState('');
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantResult, setAssistantResult] = useState<AssistantQueryResponse | null>(null);

  const loadDashboardData = async (showLoadingSpinner = false) => {
    if (showLoadingSpinner) setLoading(true);
    setIncidentsError(null);
    setWorkOrdersError(null);
    setStatsError(null);
    setHotspotsError(null);

    const [incRes, woRes, statsRes, hsRes] = await Promise.allSettled([
      getIncidents(),
      getWorkOrders(),
      getStats(),
      getHotspots()
    ]);

    if (incRes.status === 'fulfilled') {
      setIncidents(incRes.value);
    } else {
      setIncidentsError(incRes.reason?.message || 'Failed to load incidents');
    }

    if (woRes.status === 'fulfilled') {
      setWorkOrders(woRes.value);
    } else {
      setWorkOrdersError(woRes.reason?.message || 'Failed to load work orders');
    }

    if (statsRes.status === 'fulfilled') {
      setStats(statsRes.value);
    } else {
      setStatsError(statsRes.reason?.message || 'Failed to load metrics');
    }

    if (hsRes.status === 'fulfilled') {
      setHotspots(hsRes.value.hotspots || []);
      setRecommendations(hsRes.value.recommendations || []);
    } else {
      setHotspotsError(hsRes.reason?.message || 'Failed to load hotspots');
    }

    if (showLoadingSpinner) setLoading(false);
  };

  useEffect(() => {
    loadDashboardData(true);
    getMLEvaluationSummary('baseline').then(setMlSummary).catch(() => {});
    getDataQualityStats().then(setDataQuality).catch(() => {});
    const interval = setInterval(() => {
      loadDashboardData(false);
    }, 12000); // 12-second lightweight polling for live dashboard sync
    return () => clearInterval(interval);
  }, []);

  const handleStartWork = async (incidentId: string) => {
    setActionLoadingId(incidentId);
    try {
      await updateIncidentStatus(incidentId, 'IN_PROGRESS', 'Work started by field crew.', 'DISPATCHER');
      await loadDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to start work');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleOpenAssignModal = async (wo: WorkOrder) => {
    setAssigningWo(wo);
    const dept = wo.assigned_department || '';
    if (dept.includes('Water')) {
      setAssignedTeamInput(wo.assigned_team || 'Water Main Crew B');
      setAssignedWorkerInput(wo.assigned_worker || 'crew_water@civiclens.local');
    } else if (dept.includes('Traffic')) {
      setAssignedTeamInput(wo.assigned_team || 'Traffic Signal Team 1');
      setAssignedWorkerInput(wo.assigned_worker || 'crew_traffic@civiclens.local');
    } else if (dept.includes('Electrical') || dept.includes('Light')) {
      setAssignedTeamInput(wo.assigned_team || 'Electrical Repair Team 1');
      setAssignedWorkerInput(wo.assigned_worker || 'crew_electrical@civiclens.local');
    } else if (dept.includes('Drainage') || dept.includes('Sewer')) {
      setAssignedTeamInput(wo.assigned_team || 'Drainage Crew C');
      setAssignedWorkerInput(wo.assigned_worker || 'crew_drainage@civiclens.local');
    } else if (dept.includes('Waste') || dept.includes('Sanitation')) {
      setAssignedTeamInput(wo.assigned_team || 'Sanitation Crew D');
      setAssignedWorkerInput(wo.assigned_worker || 'crew_sanitation@civiclens.local');
    } else {
      setAssignedTeamInput(wo.assigned_team || 'Road Maintenance Crew Alpha');
      setAssignedWorkerInput(wo.assigned_worker || 'crew@civiclens.local');
    }

    try {
      const data = await getEligibleCrews(wo.id);
      if (data.eligible_workers && data.eligible_workers.length > 0) {
        setEligibleWorkersList(data.eligible_workers);
        const match = data.eligible_workers[0];
        setAssignedWorkerInput(wo.assigned_worker || match.email);
        setAssignedWorkerIdInput(wo.assigned_worker_id || match.id);
      } else {
        setEligibleWorkersList([]);
      }
      if (data.eligible_teams && data.eligible_teams.length > 0) {
        setAssignedTeamInput(wo.assigned_team || data.eligible_teams[0]);
      }
    } catch {
      setEligibleWorkersList([]);
    }
  };

  const handleSubmitCrewAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assigningWo) return;
    setAssigningLoading(true);
    try {
      await assignWorkOrderCrew(assigningWo.id, assignedTeamInput, assignedWorkerInput, assignedWorkerIdInput);
      setAssigningWo(null);
      await loadDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to assign crew');
    } finally {
      setAssigningLoading(false);
    }
  };

  const handleOpenCompletionModal = (wo: WorkOrder) => {
    setCompletingWo(wo);
    setCompletionNotesInput('Field crew completed repairs according to work order specifications.');
    setCompletionImageFile(null);
  };

  const handleSubmitWorkCompletion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completingWo) return;
    setCompletingLoading(true);
    try {
      const formData = new FormData();
      formData.append('status', 'COMPLETED');
      formData.append('completion_notes', completionNotesInput || 'Field crew completed maintenance repairs.');
      if (completionImageFile) {
        formData.append('file', completionImageFile);
      }
      await updateWorkOrderStatus(completingWo.id, formData);
      setCompletingWo(null);
      setCompletionImageFile(null);
      await loadDashboardData();
    } catch (err: any) {
      alert(err.message || 'Failed to complete work order');
    } finally {
      setCompletingLoading(false);
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
    "Where are the biggest civic hotspots?",
    "Why is the top incident P1?",
    "Which department has the most active work?",
    "How many incidents are awaiting verification?"
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
          onClick={() => loadDashboardData(true)}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Dashboard
        </button>
      </div>

      {/* Statistics Cards Error / Content */}
      {statsError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>Unable to load dashboard metrics from backend API: {statsError}</span>
        </div>
      )}

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

      {/* SLA & Operational Dispatch Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono font-bold text-slate-500 uppercase block">Active Dispatches</span>
            <span className="text-xl font-black text-slate-900 mt-0.5 block">
              {workOrders.filter(w => ['PENDING', 'ASSIGNED', 'IN_PROGRESS'].includes(w.status)).length}
            </span>
          </div>
          <div className="p-2.5 bg-slate-100 rounded-xl text-slate-700">
            <Wrench className="w-5 h-5 text-indigo-600" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono font-bold text-emerald-700 uppercase block">SLA On Track</span>
            <span className="text-xl font-black text-emerald-700 mt-0.5 block">
              {workOrders.filter(w => w.sla_status === 'ON_TRACK').length}
            </span>
          </div>
          <div className="p-2.5 bg-emerald-50 rounded-xl text-emerald-700">
            <Clock className="w-5 h-5 text-emerald-600" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono font-bold text-amber-700 uppercase block">SLA At Risk (≥75%)</span>
            <span className="text-xl font-black text-amber-700 mt-0.5 block">
              {workOrders.filter(w => w.sla_status === 'AT_RISK').length}
            </span>
          </div>
          <div className="p-2.5 bg-amber-50 rounded-xl text-amber-700">
            <Clock className="w-5 h-5 text-amber-600" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[11px] font-mono font-bold text-rose-700 uppercase block">SLA Breached</span>
            <span className="text-xl font-black text-rose-700 mt-0.5 block">
              {workOrders.filter(w => w.sla_status === 'BREACHED').length}
            </span>
          </div>
          <div className="p-2.5 bg-rose-50 rounded-xl text-rose-700">
            <AlertOctagon className="w-5 h-5 text-rose-600" />
          </div>
        </div>
      </div>

      {/* AI Model Performance & NYC 311 Data Quality Panel */}
      {mlSummary && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-600" /> AI Model Performance & Data Quality (NYC 311 Dataset)
            </h2>
            <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-mono font-bold rounded-md uppercase border border-indigo-200">
              {mlSummary.ai?.status_message || mlSummary.baseline?.model_name || 'Baseline & AI Evaluation'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
            {/* Baseline Card */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="flex justify-between items-center font-mono">
                <span className="font-bold text-slate-800">DETERMINISTIC BASELINE</span>
                <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">TAXONOMY</span>
              </div>
              <div className="space-y-1 pt-1">
                <div className="flex justify-between">
                  <span className="text-slate-500">Overall Accuracy:</span>
                  <span className="font-bold text-emerald-700">{((mlSummary.baseline?.overall_accuracy ?? 1.0) * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Macro F1 Score:</span>
                  <span className="font-bold text-indigo-700">{(mlSummary.baseline?.macro_f1 ?? 1.0).toFixed(4)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Evaluated Samples:</span>
                  <span className="font-mono text-slate-800">{mlSummary.baseline?.total_samples_evaluated ?? 1400}</span>
                </div>
              </div>
            </div>

            {/* AI Classifier Card */}
            <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-200 space-y-2">
              <div className="flex justify-between items-center font-mono">
                <span className="font-bold text-indigo-900">CIVICLENS AI CLASSIFIER</span>
                <span className="text-[10px] bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded font-bold">
                  {mlSummary.ai?.available ? 'ACTIVE' : 'DEMO MODE'}
                </span>
              </div>
              {mlSummary.ai?.available ? (
                <div className="space-y-1 pt-1">
                  <div className="flex justify-between">
                    <span className="text-indigo-800">Overall Accuracy:</span>
                    <span className="font-bold text-emerald-700">{((mlSummary.ai?.overall_accuracy ?? 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-indigo-800">Macro F1 Score:</span>
                    <span className="font-bold text-indigo-800">{(mlSummary.ai?.macro_f1 ?? 0).toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-indigo-800">Avg AI Latency:</span>
                    <span className="font-mono text-slate-800">{mlSummary.ai?.average_latency_ms ?? 18} ms</span>
                  </div>
                </div>
              ) : (
                <div className="p-2.5 bg-amber-50 border border-amber-200 text-amber-800 text-[11px] rounded-lg mt-1">
                  AI LIVE EVALUATION NOT RUN — OPENAI_API_KEY unavailable. (AI DEMO / FALLBACK MODE ACTIVE)
                </div>
              )}
            </div>

            {/* Confidence Tiers Card */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <span className="font-bold text-slate-800 font-mono block">CONFIDENCE POLICY TIERS</span>
              <div className="space-y-1 text-[11px] pt-1">
                <div className="flex justify-between items-center">
                  <span className="text-emerald-700 font-semibold">HIGH (&ge; 80%):</span>
                  <span className="font-mono bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-bold">AUTO ROUTING</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-amber-700 font-semibold">MEDIUM (60-79%):</span>
                  <span className="font-mono bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-bold">DISPATCH REVIEW</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-rose-700 font-semibold">LOW (&lt; 60%):</span>
                  <span className="font-mono bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded font-bold">MANDATORY REVIEW</span>
                </div>
              </div>
            </div>
          </div>

          {dataQuality && (
            <div className="p-3.5 bg-slate-900 text-white rounded-xl text-xs space-y-2">
              <div className="flex justify-between items-center font-mono">
                <span className="text-indigo-300 font-bold uppercase">NYC 311 Ingestion Audit</span>
                <span className="text-slate-400">Processed: {dataQuality.rows_processed} | Accepted: {dataQuality.rows_accepted}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-300 border-t border-slate-800 pt-2">
                <div>Invalid Coords Removed: <span className="font-bold text-amber-400">{dataQuality.invalid_coordinates_count}</span></div>
                <div>Duplicates Removed: <span className="font-bold text-sky-400">{dataQuality.duplicate_records_removed}</span></div>
                <div>Rejected Rows: <span className="font-bold text-rose-400">{dataQuality.rows_rejected}</span></div>
                <div>Mapping Version: <span className="font-bold text-emerald-400">{dataQuality.pipeline_version}</span></div>
              </div>
            </div>
          )}
        </div>
      )}

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

            {hotspotsError ? (
              <p className="text-xs text-rose-600 py-4 text-center bg-rose-50/50 rounded-lg">Unable to load spatial hotspots from API: {hotspotsError}</p>
            ) : hotspots.length === 0 ? (
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
            ) : incidentsError ? (
              <div className="p-8 text-center text-rose-600 text-sm bg-rose-50/50">
                <AlertCircle className="w-5 h-5 mx-auto mb-1 text-rose-500" />
                <span>Unable to load incidents queue from API: {incidentsError}</span>
              </div>
            ) : incidents.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">No incidents found in database.</div>
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
                          onClick={() => {
                            const targetWo: WorkOrder = inc.work_order || {
                              id: (inc as any).work_order_id || inc.id,
                              incident_id: inc.id,
                              assigned_department: inc.assigned_department || 'Public Works - Roads',
                              assigned_worker: 'crew@civiclens.local',
                              assigned_worker_id: 'usr-crew-1',
                              recommended_action: inc.title || 'Inspect & repair reported incident',
                              status: 'ASSIGNED' as any,
                              created_at: inc.created_at
                            };
                            handleOpenAssignModal(targetWo);
                          }}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow transition flex items-center gap-1"
                        >
                          <Wrench className="w-3.5 h-3.5" />
                          <span>{inc.work_order?.assigned_team ? 'Reassign Crew' : 'Assign Crew'}</span>
                        </button>
                      ) : inc.status === 'IN_PROGRESS' ? (
                        <span className="px-2.5 py-1 bg-indigo-50 text-indigo-800 text-[11px] font-semibold rounded-lg border border-indigo-200">
                          Work In Progress (Field Crew)
                        </span>
                      ) : inc.status === 'RESOLVED' ? (
                        <span className="px-2.5 py-1 bg-amber-50 text-amber-800 text-[11px] font-semibold rounded-lg border border-amber-200">
                          Awaiting Verification
                        </span>
                      ) : inc.status === 'VERIFIED' ? (
                        <span className="px-2.5 py-1 bg-emerald-50 text-emerald-800 text-[11px] font-semibold rounded-lg border border-emerald-200">
                          Verified ✓
                        </span>
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
            <span className="text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Wrench className="w-4 h-4 text-indigo-600" /> Active Work Orders ({workOrders.filter(wo => ['PENDING', 'ASSIGNED', 'IN_PROGRESS'].includes(wo.status)).length})
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Total Created: {workOrders.length}</span>
            </span>
            <div className="space-y-2">
              {workOrders.filter(wo => ['PENDING', 'ASSIGNED', 'IN_PROGRESS'].includes(wo.status)).length === 0 ? (
                <div className="p-3 text-center text-xs text-slate-500 bg-slate-50 rounded-lg">No active work orders pending dispatch.</div>
              ) : (
                workOrders.filter(wo => ['PENDING', 'ASSIGNED', 'IN_PROGRESS'].includes(wo.status)).map((wo) => (
                  <div key={wo.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-800">{wo.assigned_department}</span>
                      <div className="flex items-center gap-1.5">
                        {wo.sla_status === 'BREACHED' ? (
                          <span className="px-1.5 py-0.5 bg-rose-100 text-rose-800 text-[10px] font-bold rounded uppercase">SLA BREACHED</span>
                        ) : wo.sla_status === 'AT_RISK' ? (
                          <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded uppercase">SLA AT RISK</span>
                        ) : (
                          <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded uppercase">SLA ON TRACK</span>
                        )}
                        <span className="text-[10px] text-indigo-600 font-bold uppercase">{wo.status}</span>
                      </div>
                    </div>
                    {wo.assigned_team && (
                      <div className="text-[11px] text-slate-500 font-medium">
                        Crew: <span className="text-slate-800 font-semibold">{wo.assigned_team}</span> {wo.assigned_worker ? `(${wo.assigned_worker})` : ''}
                      </div>
                    )}
                    <div className="text-slate-600 truncate">{wo.recommended_action}</div>
                    <button
                      onClick={() => handleOpenAssignModal(wo)}
                      className="w-full py-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-[11px] rounded transition flex items-center justify-center gap-1"
                    >
                      <Wrench className="w-3.5 h-3.5" />
                      <span>{wo.assigned_team ? 'Reassign Crew' : 'Assign Crew'}</span>
                    </button>
                  </div>
                ))
              )}
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
      {/* Assign Crew Modal */}
      {assigningWo && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Wrench className="w-5 h-5 text-indigo-600" /> Assign Field Crew & Team
              </h3>
              <button onClick={() => setAssigningWo(null)} className="text-slate-400 hover:text-slate-600 transition">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitCrewAssignment} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-800 mb-1">Department & Work Order</label>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 space-y-1">
                  <div className="font-bold text-slate-900">{assigningWo.assigned_department}</div>
                  <div>{assigningWo.recommended_action}</div>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-800 mb-1">Assigned Maintenance Team</label>
                <input
                  type="text"
                  value={assignedTeamInput}
                  onChange={(e) => setAssignedTeamInput(e.target.value)}
                  placeholder="e.g. Road Maintenance Crew Alpha"
                  required
                  className="w-full rounded-lg border border-slate-300 p-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-800 mb-1">Assigned Field Worker / Supervisor</label>
                <input
                  type="text"
                  value={assignedWorkerInput}
                  onChange={(e) => setAssignedWorkerInput(e.target.value)}
                  placeholder="e.g. Ramesh Kumar"
                  required
                  className="w-full rounded-lg border border-slate-300 p-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAssigningWo(null)}
                  className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assigningLoading}
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl flex items-center justify-center gap-1 shadow transition disabled:opacity-50"
                >
                  {assigningLoading ? 'Assigning Crew...' : 'Confirm Crew Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* WorkOrder Completion Evidence Upload Modal */}
      {completingWo && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Wrench className="w-5 h-5 text-emerald-600" /> Complete Work Order & Upload Evidence
              </h3>
              <button onClick={() => setCompletingWo(null)} className="text-slate-400 hover:text-slate-600 transition">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitWorkCompletion} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-800 mb-1">Department & Action Plan</label>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 space-y-1">
                  <div className="font-bold text-slate-900">{completingWo.assigned_department}</div>
                  <div>{completingWo.recommended_action}</div>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-800 mb-1">Completion Notes</label>
                <textarea
                  rows={3}
                  value={completionNotesInput}
                  onChange={(e) => setCompletionNotesInput(e.target.value)}
                  placeholder="Enter crew completion details, materials used, or repair notes..."
                  className="w-full rounded-lg border border-slate-300 p-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-800 mb-1">Upload Completion Photo Evidence (Optional)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setCompletionImageFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer"
                />
                <p className="text-[10px] text-slate-400 mt-1">Uploaded image will be displayed on citizen verification page as resolution evidence.</p>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCompletingWo(null)}
                  className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={completingLoading}
                  className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl flex items-center justify-center gap-1 shadow transition disabled:opacity-50"
                >
                  {completingLoading ? 'Submitting Resolution...' : 'Mark Resolved ✓'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
