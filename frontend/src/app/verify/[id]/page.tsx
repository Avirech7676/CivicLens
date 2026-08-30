'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CheckCircle2, ShieldCheck, FileText, Camera, Send, AlertCircle, Clock } from 'lucide-react';
import { getIncident, verifyIncidentResolution, getMediaUrl } from '@/lib/api';
import { Incident } from '@/types';

export default function CitizenVerification() {
  const { id } = useParams();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState('');
  const [verified, setVerified] = useState(false);
  const [reopened, setReopened] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      getIncident(id as string)
        .then((data) => {
          setIncident(data);
          if (data.status === 'VERIFIED') setVerified(true);
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const handleVerify = async (verifiedFixed: boolean) => {
    if (!incident || incident.status !== 'RESOLVED') return;
    setSubmitting(true);
    setError(null);

    try {
      const updated = await verifyIncidentResolution(incident.id, verifiedFixed, notes);
      setIncident(updated);
      if (verifiedFixed) {
        setVerified(true);
        setReopened(false);
      } else {
        setVerified(false);
        setReopened(true);
      }
    } catch (err: any) {
      setError(err.message || 'Verification failed');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusUnreadyMessage = (status: string) => {
    switch (status) {
      case 'SUBMITTED':
        return "Your report has been received and is waiting for review.";
      case 'TRIAGED':
        return "Your report is being reviewed.";
      case 'ASSIGNED':
        return "The issue has been assigned to the responsible department.";
      case 'IN_PROGRESS':
        return "Repair work is currently in progress.";
      default:
        return "Verification is not available yet for this incident.";
    }
  };

  if (loading) {
    return <div className="py-12 text-center text-slate-500 font-medium">Loading verification data...</div>;
  }

  if (error || !incident) {
    return <div className="p-6 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-center">Failed: {error}</div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Verification Header */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-emerald-600 font-semibold text-xs uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" /> Citizen Resolution Verification
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Verify Resolution for Incident #{incident.id.slice(0, 8)}</h1>
        <p className="text-xs text-slate-500">
          Review municipal resolution photos and confirm whether the hazard has been satisfactorily resolved.
        </p>
      </div>

      {/* Comparison Evidence Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Before / Initial Evidence */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Initial Complaint Evidence</span>
          <p className="text-xs text-slate-700 bg-slate-50 p-3 rounded border border-slate-100">{incident.description}</p>
          {incident.reports?.[0]?.image_path ? (
            <img src={getMediaUrl(incident.reports[0].image_path)} alt="Original" className="rounded-lg h-44 w-full object-cover border" />
          ) : (
            <div className="h-44 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400 text-xs font-mono">No initial photo</div>
          )}
        </div>

        {/* After / Work Order Resolution Evidence */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider block">Municipal Repair Photo</span>
          <p className="text-xs text-slate-700 bg-emerald-50/50 p-3 rounded border border-emerald-100">
            {incident.work_order?.completion_notes || 'Municipal field crew completed repairs according to work order.'}
          </p>
          {incident.work_order?.completion_image_path ? (
            <img src={getMediaUrl(incident.work_order.completion_image_path)} alt="Resolution" className="rounded-lg h-44 w-full object-cover border" />
          ) : (
            <div className="h-44 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400 text-xs font-mono">No completion photo was uploaded.</div>
          )}
        </div>
      </div>

      {/* Action Card */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-4">
        {incident.status === 'VERIFIED' || verified ? (
          <div className="p-6 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
            <h3 className="font-bold text-base">Incident Verified as Satisfactorily Resolved</h3>
            <p className="text-xs text-emerald-700">Thank you for verifying and helping keep your community safe.</p>
          </div>
        ) : reopened ? (
          <div className="p-6 bg-amber-50 border border-amber-200 text-amber-900 rounded-xl text-center space-y-2">
            <AlertCircle className="w-10 h-10 text-amber-600 mx-auto" />
            <h3 className="font-bold text-base">Issue Reported Still Not Fixed — Reopened</h3>
            <p className="text-xs text-amber-800">
              The incident and work order have been reopened to IN_PROGRESS status and returned to municipal dispatch for re-inspection.
            </p>
          </div>
        ) : incident.status === 'RESOLVED' ? (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-800">Submit Verification Feedback</h3>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Provide optional confirmation or feedback on the repair..."
              className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                onClick={() => handleVerify(true)}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3.5 px-4 rounded-xl shadow transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Verify Fixed ✓</span>
              </button>
              <button
                onClick={() => handleVerify(false)}
                disabled={submitting}
                className="bg-rose-600 hover:bg-rose-700 text-white font-semibold py-3.5 px-4 rounded-xl shadow transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <AlertCircle className="w-4 h-4" />
                <span>Still Not Fixed (Reopen)</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6 bg-slate-50 border border-slate-200 text-slate-700 rounded-xl text-center space-y-2">
            <Clock className="w-8 h-8 text-sky-600 mx-auto" />
            <h3 className="font-bold text-sm text-slate-800">Resolution Pending</h3>
            <p className="text-xs text-slate-600">{getStatusUnreadyMessage(incident.status)}</p>
            <div className="pt-2">
              <span className="inline-block text-[11px] font-mono px-3 py-1 bg-sky-100 text-sky-800 font-semibold rounded-full border border-sky-200">
                Current Status: {incident.status}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
