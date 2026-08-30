'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Camera, MapPin, Send, AlertCircle, CheckCircle2, Sparkles, Image as ImageIcon } from 'lucide-react';
import { submitReport } from '@/lib/api';

export default function CitizenPortal() {
  const router = useRouter();
  const [description, setDescription] = useState('');
  const [address, setAddress] = useState('Main Gate Road, Campus Area');
  const [latitude, setLatitude] = useState<number>(28.5450);
  const [longitude, setLongitude] = useState<number>(77.1926);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) {
      setError('Please provide a description of the issue.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('description', description);
      formData.append('address', address);
      formData.append('latitude', latitude.toString());
      formData.append('longitude', longitude.toString());
      if (imageFile) {
        formData.append('file', imageFile);
      }

      const response = await submitReport(formData);
      const targetIncidentId = response.incident_id || response.duplicate_info?.matched_incident_id;
      if (targetIncidentId) {
        router.push(`/incident/${targetIncidentId}`);
      } else {
        router.push('/admin');
      }
    } catch (err: any) {
      setError(err.message || 'Error submitting report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-sky-950 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-800">
        <div className="flex items-center gap-2 text-sky-400 font-semibold text-xs tracking-wider uppercase mb-2">
          <Sparkles className="w-4 h-4" /> AI Incident Resolution Portal
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Report a Community Incident</h1>
        <p className="mt-2 text-slate-300 text-sm sm:text-base max-w-xl">
          Describe the civic issue, attach photographic evidence, and submit. CivicLens will analyze, classify, and generate an actionable work order.
        </p>
      </div>

      {/* Main Form Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 sm:p-8 space-y-6">
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-sm flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Complaint Description */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 mb-2">
              Issue Description <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Large 2-foot hazardous pothole near the crosswalk causing traffic slowdowns and rim damage..."
              className="w-full rounded-lg border border-slate-300 p-3 text-slate-900 text-sm focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none transition"
              required
            />
          </div>

          {/* Evidence Upload */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 mb-2">
              Photo Evidence
            </label>
            <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-slate-300 border-dashed rounded-xl hover:border-sky-500 transition cursor-pointer bg-slate-50 relative">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div className="space-y-2 text-center">
                {previewUrl ? (
                  <div className="relative w-48 h-32 mx-auto rounded-lg overflow-hidden border border-slate-300">
                    <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                  </div>
                ) : (
                  <>
                    <Camera className="mx-auto h-10 w-10 text-slate-400" />
                    <div className="flex text-sm text-slate-600">
                      <span className="relative font-medium text-sky-600 hover:text-sky-500">
                        Upload a photo
                      </span>
                      <p className="pl-1">or drag and drop</p>
                    </div>
                    <p className="text-xs text-slate-500">PNG, JPG up to 10MB</p>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Location Section */}
          <div className="space-y-3 pt-2">
            <label className="block text-sm font-semibold text-slate-800">
              Location Details
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Street Address or Landmark"
                  className="w-full pl-9 rounded-lg border border-slate-300 p-2.5 text-slate-900 text-sm focus:ring-2 focus:ring-sky-500 outline-none"
                />
              </div>
            </div>
            
            {/* Location Coordinate Preview Placeholder */}
            <div className="p-3 bg-slate-100 rounded-lg text-xs font-mono text-slate-600 flex justify-between items-center border border-slate-200">
              <span>GPS Coordinates: {latitude.toFixed(4)}, {longitude.toFixed(4)}</span>
              <span className="text-emerald-600 font-medium">GPS Locked</span>
            </div>
          </div>

          {/* Processing Progress Bar during analysis */}
          {loading && (
            <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-sky-900">
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-sky-600 animate-spin" />
                  AI Incident Analysis Engine Active
                </span>
                <span>Processing...</span>
              </div>
              <div className="text-xs text-slate-600 space-y-1 font-mono">
                <div className="flex items-center gap-2 text-sky-800 font-bold">✓ Uploading complaint & photographic evidence...</div>
                <div className="flex items-center gap-2 text-sky-800">→ Executing multimodal classification & hazard detection...</div>
                <div className="flex items-center gap-2 text-slate-400">⏱ Assessing severity level & confidence scoring...</div>
                <div className="flex items-center gap-2 text-slate-400">⏱ Generating structured incident record...</div>
              </div>
            </div>
          )}

          {/* Submit CTA */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-3.5 px-4 rounded-xl shadow-md transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <span>Analyzing & Creating Incident...</span>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Submit Complaint to CivicLens</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
