'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CheckCircle2, ShieldCheck, FileText, Camera, Send, AlertCircle } from 'lucide-react';
import { getIncident, verifyIncidentResolution } from '@/lib/api';
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
    if (!incident) return;
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
      setError(err.message || 'Verification submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="py-12 text-center text-slate-500 font-medium">Loading repair photos...</div>;
  }

  if (error || !incident) {
    return <div className="p-6 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-center">Unable to load report: {error}</div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Verification Header */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-emerald-600 font-semibold text-xs uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" /> Citizen Feedback
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Did this fix the problem?</h1>
        <p className="text-xs text-slate-600">
          Please review the repair photos below and let us know if the issue has been satisfactorily resolved.
        </p>
      </div>

      {/* Comparison Evidence Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Before / Initial Evidence */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Initial Report Photo</span>
          <p className="text-xs text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100">{incident.description}</p>
          {incident.reports?.[0]?.image_path ? (
            <img src={`http://localhost:8000/static/${incident.reports[0].image_path.split('/').pop()}`} alt="Original" className="rounded-xl h-44 w-full object-cover border" />
          ) : (
            <div className="h-44 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400 text-xs font-medium">No initial photo</div>
          )}
        </div>

        {/* After / Work Order Resolution Evidence */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider block">Repair Photo from Department</span>
          <p className="text-xs text-slate-700 bg-emerald-50/50 p-3 rounded-xl border border-emerald-100">
            {incident.work_order?.completion_notes || 'Repair completed by maintenance team.'}
          </p>
          {incident.work_order?.completion_image_path ? (
            <img src={`http://localhost:8000/static/${incident.work_order.completion_image_path.split('/').pop()}`} alt="Resolution" className="rounded-xl h-44 w-full object-cover border" />
          ) : (
            <div className="h-44 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400 text-xs font-medium">Repair photo attached by department</div>
          )}
        </div>
      </div>

      {/* Action Card */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
        {verified ? (
          <div className="p-6 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
            <h3 className="font-bold text-base">You confirmed the problem is fixed!</h3>
            <p className="text-xs text-emerald-700">Thank you for confirming. Your feedback helps improve our city.</p>
          </div>
        ) : reopened ? (
          <div className="p-6 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl text-center space-y-2">
            <AlertCircle className="w-10 h-10 text-amber-600 mx-auto" />
            <h3 className="font-bold text-base">The problem is still there — Sent back to department</h3>
            <p className="text-xs text-amber-800">
              Your feedback has been sent back to the department for re-inspection and work order reopening.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Add any comments (Optional)</h3>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. The pothole is filled smoothly, thank you! OR The surface is still uneven..."
              className="w-full rounded-xl border border-slate-300 p-3.5 text-slate-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                onClick={() => handleVerify(true)}
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 px-4 rounded-xl shadow transition flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Yes, the problem is fixed ✓</span>
              </button>
              <button
                onClick={() => handleVerify(false)}
                disabled={submitting}
                className="bg-rose-600 hover:bg-rose-700 text-white font-bold py-3.5 px-4 rounded-xl shadow transition flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
              >
                <AlertCircle className="w-4 h-4" />
                <span>No, the problem is still there</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
