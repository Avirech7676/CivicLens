'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Wrench, CheckCircle2, Clock, AlertCircle, MapPin, Building2, ShieldAlert, FileText, X, ArrowUpRight } from 'lucide-react';
import { getMyWorkOrders, getWorkOrders, updateWorkOrderStatus, updateIncidentStatus } from '@/lib/api';
import { WorkOrder } from '@/types';
import { useAuth } from '@/context/AuthContext';

export default function FieldCrewDashboard() {
  const { user } = useAuth();
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Completion Modal State
  const [completingWo, setCompletingWo] = useState<WorkOrder | null>(null);
  const [completionNotes, setCompletionNotes] = useState('');
  const [completionImage, setCompletionImage] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const loadCrewWorkOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMyWorkOrders();
      setWorkOrders(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load assigned field work orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCrewWorkOrders();
  }, []);

  const handleStartWork = async (wo: WorkOrder) => {
    setActionLoadingId(wo.id);
    try {
      await updateWorkOrderStatus(wo.id, (() => {
        const fd = new FormData();
        fd.append('status', 'IN_PROGRESS');
        return fd;
      })());
      await loadCrewWorkOrders();
    } catch (err: any) {
      alert(err.message || 'Failed to start field work');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleOpenCompletionModal = (wo: WorkOrder) => {
    setCompletingWo(wo);
    setCompletionNotes('Field crew completed repairs according to work order specifications.');
    setCompletionImage(null);
  };

  const handleSubmitWorkCompletion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completingWo) return;
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('status', 'COMPLETED');
      formData.append('completion_notes', completionNotes || 'Field crew completed maintenance repairs.');
      if (completionImage) {
        formData.append('file', completionImage);
      }
      await updateWorkOrderStatus(completingWo.id, formData);
      setCompletingWo(null);
      setCompletionImage(null);
      await loadCrewWorkOrders();
    } catch (err: any) {
      alert(err.message || 'Failed to mark work order completed');
    } finally {
      setSubmitting(false);
    }
  };

  const assignedOrders = workOrders.filter(wo => ['PENDING', 'ASSIGNED'].includes(wo.status));
  const inProgressOrders = workOrders.filter(wo => wo.status === 'IN_PROGRESS');
  const completedOrders = workOrders.filter(wo => wo.status === 'COMPLETED');

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Field Crew Header */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-md uppercase font-mono">
              FIELD CREW DASHBOARD
            </span>
            {user?.department && (
              <span className="text-xs font-semibold text-slate-500 font-mono">
                &bull; {user.department}
              </span>
            )}
          </div>
          <h1 className="text-2xl font-black text-slate-900">Assigned Field Operations</h1>
          <p className="text-xs text-slate-500 mt-1">
            Logged as <span className="font-semibold text-slate-800">{user?.full_name || 'Field Crew Worker'}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-emerald-50 text-emerald-800 font-bold text-xs rounded-xl border border-emerald-200">
            {assignedOrders.length + inProgressOrders.length} Active Dispatches
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* SECTION 1: MY ASSIGNED WORK */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-600" /> 1. My Assigned Work ({assignedOrders.length})
        </h2>

        {assignedOrders.length === 0 ? (
          <div className="p-6 bg-white rounded-xl border border-slate-200 text-center text-xs text-slate-500">
            No pending/assigned work orders awaiting dispatch.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {assignedOrders.map((wo) => (
              <div key={wo.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-xs text-slate-800 bg-slate-100 px-2.5 py-1 rounded-md">
                      WO-{wo.id.slice(0, 8).toUpperCase()}
                    </span>
                    <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 font-bold text-xs rounded-md">
                      {wo.assigned_department}
                    </span>
                    {wo.sla_status === 'BREACHED' ? (
                      <span className="px-2 py-0.5 bg-rose-100 text-rose-800 font-bold text-[10px] rounded uppercase">SLA BREACHED</span>
                    ) : wo.sla_status === 'AT_RISK' ? (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-bold text-[10px] rounded uppercase">SLA AT RISK</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold text-[10px] rounded uppercase">SLA ON TRACK</span>
                    )}
                  </div>

                  <span className="px-3 py-1 bg-amber-100 text-amber-900 font-mono font-bold text-xs rounded-lg uppercase border border-amber-200">
                    {wo.status}
                  </span>
                </div>

                <div className="space-y-3 text-xs text-slate-700">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="font-bold text-slate-900 block">Required Action Procedure</span>
                    <p className="whitespace-pre-line leading-relaxed">{wo.recommended_action}</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                      <span className="font-bold text-slate-900 block">Required Tools & Materials</span>
                      <p className="whitespace-pre-line leading-relaxed">{wo.required_materials || 'Standard maintenance kit'}</p>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                      <span className="font-bold text-slate-900 block">Safety & PPE Precautions</span>
                      <p className="whitespace-pre-line leading-relaxed">{wo.safety_precautions || 'High-visibility safety vests & cones'}</p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-2">
                  <Link
                    href={`/incident/${wo.incident_id}`}
                    className="text-xs text-indigo-600 font-semibold hover:underline flex items-center gap-1"
                  >
                    <span>View Incident Telemetry #{wo.incident_id.slice(0, 8)}</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>

                  <button
                    onClick={() => handleStartWork(wo)}
                    disabled={actionLoadingId === wo.id}
                    className="w-full sm:w-auto px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow transition disabled:opacity-50"
                  >
                    {actionLoadingId === wo.id ? 'Starting Work...' : 'Start Field Work'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECTION 2: ACTIVE WORK (IN_PROGRESS) */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Wrench className="w-4 h-4 text-indigo-600" /> 2. Active Work ({inProgressOrders.length})
        </h2>

        {inProgressOrders.length === 0 ? (
          <div className="p-6 bg-white rounded-xl border border-slate-200 text-center text-xs text-slate-500">
            No work orders currently in progress.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {inProgressOrders.map((wo) => (
              <div key={wo.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-xs text-slate-800 bg-slate-100 px-2.5 py-1 rounded-md">
                      WO-{wo.id.slice(0, 8).toUpperCase()}
                    </span>
                    <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 font-bold text-xs rounded-md">
                      {wo.assigned_department}
                    </span>
                  </div>

                  <span className="px-3 py-1 bg-indigo-600 text-white font-mono font-bold text-xs rounded-lg uppercase">
                    {wo.status}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-1">
                  <span className="font-bold text-slate-900 block">Procedure</span>
                  <p>{wo.recommended_action}</p>
                </div>

                <div className="flex justify-between items-center pt-2">
                  <Link
                    href={`/incident/${wo.incident_id}`}
                    className="text-xs text-indigo-600 font-semibold hover:underline flex items-center gap-1"
                  >
                    <span>View Telemetry</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>

                  <button
                    onClick={() => handleOpenCompletionModal(wo)}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow transition flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Complete Work & Upload Evidence</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECTION 3: COMPLETED WORK */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" /> 3. Completed Work ({completedOrders.length})
        </h2>

        {completedOrders.length === 0 ? (
          <div className="p-6 bg-white rounded-xl border border-slate-200 text-center text-xs text-slate-500">
            No completed work orders recorded.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {completedOrders.map((wo) => (
              <div key={wo.id} className="bg-white p-4 rounded-xl border border-slate-200 text-xs flex justify-between items-center">
                <div className="space-y-1">
                  <span className="font-mono font-bold text-slate-800">WO-{wo.id.slice(0, 8).toUpperCase()}</span>
                  <p className="text-slate-600 truncate max-w-md">{wo.completion_notes || wo.recommended_action}</p>
                </div>
                <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 font-bold text-[10px] rounded uppercase">COMPLETED ✓</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Field Crew Completion Modal */}
      {completingWo && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Wrench className="w-5 h-5 text-emerald-600" /> Complete Field Work Order
              </h3>
              <button onClick={() => setCompletingWo(null)} className="text-slate-400 hover:text-slate-600 transition">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitWorkCompletion} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-800 mb-1">Department & Procedure</label>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 space-y-1">
                  <div className="font-bold text-slate-900">{completingWo.assigned_department}</div>
                  <div className="truncate">{completingWo.recommended_action}</div>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-800 mb-1">Completion Notes</label>
                <textarea
                  rows={3}
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  placeholder="Enter crew completion details, materials used, or repair notes..."
                  className="w-full rounded-lg border border-slate-300 p-2.5 text-slate-900 outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-800 mb-1">Upload Completion Photo Evidence</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setCompletionImage(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer"
                />
                <p className="text-[10px] text-slate-400 mt-1">Uploaded image will be rendered on citizen verification page as repair evidence.</p>
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
                  disabled={submitting}
                  className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl flex items-center justify-center gap-1 shadow transition disabled:opacity-50"
                >
                  {submitting ? 'Submitting Resolution...' : 'Mark Resolved ✓'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
