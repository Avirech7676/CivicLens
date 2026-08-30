'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Incident, Hotspot } from '@/types';
import { ShieldAlert, AlertTriangle, Layers, MapPin, ExternalLink, Flame } from 'lucide-react';

interface LeafletMapProps {
  incidents: Incident[];
  hotspots?: Hotspot[];
  selectedIncidentId?: string | null;
  selectedHotspotId?: string | null;
  onSelectIncident?: (id: string) => void;
  onSelectHotspot?: (hotspot: Hotspot) => void;
  className?: string;
}

export default function LeafletMap({
  incidents,
  hotspots = [],
  selectedIncidentId,
  selectedHotspotId,
  onSelectIncident,
  onSelectHotspot,
  className = "h-96 w-full rounded-2xl overflow-hidden border border-slate-200 shadow-sm"
}: LeafletMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [activeHotspot, setActiveHotspot] = useState<Hotspot | null>(null);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);

  useEffect(() => {
    // Dynamic import Leaflet Script if not present
    if (typeof window !== 'undefined' && !(window as any).L) {
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = () => setMapLoaded(true);
      document.head.appendChild(script);
    } else if (typeof window !== 'undefined' && (window as any).L) {
      setMapLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!mapLoaded || !mapRef.current || typeof window === 'undefined') return;

    const L = (window as any).L;
    if (!L) return;

    // Default center (Indian Campus / Main Gate Area)
    const defaultCenter = [28.5450, 77.1926];
    
    // Calculate bounds if points exist
    const allCoords: [number, number][] = [];
    incidents.forEach(inc => {
      if (inc.latitude && inc.longitude) allCoords.push([inc.latitude, inc.longitude]);
    });
    hotspots.forEach(hs => {
      if (hs.latitude && hs.longitude) allCoords.push([hs.latitude, hs.longitude]);
    });

    const center = allCoords.length > 0 ? allCoords[0] : defaultCenter;

    // Reset container if previously initialized
    if ((mapRef.current as any)._leaflet_map) {
      (mapRef.current as any)._leaflet_map.remove();
    }

    const map = L.map(mapRef.current).setView(center, 14);
    (mapRef.current as any)._leaflet_map = map;

    // OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors | CivicLens Command Center'
    }).addTo(map);

    // 1. Render Translucent Spatial Hotspot Circles
    hotspots.forEach(hs => {
      const isSelected = selectedHotspotId === hs.hotspot_id;
      let strokeColor = '#ea580c'; // Orange
      let fillColor = 'rgba(234, 88, 12, 0.25)';

      if (hs.hotspot_level === 'CRITICAL') {
        strokeColor = '#dc2626'; // Red
        fillColor = 'rgba(220, 38, 38, 0.30)';
      } else if (hs.hotspot_level === 'EMERGING') {
        strokeColor = '#d97706'; // Amber
        fillColor = 'rgba(217, 119, 6, 0.25)';
      }

      const circle = L.circle([hs.latitude, hs.longitude], {
        color: strokeColor,
        weight: isSelected ? 4 : 2,
        fillColor: fillColor,
        fillOpacity: 0.35,
        radius: hs.radius_meters || 250
      }).addTo(map);

      // Hotspot click popup
      const popupContent = `
        <div style="font-family: sans-serif; min-width: 200px; padding: 4px;">
          <div style="font-size: 10px; font-weight: bold; color: ${strokeColor}; text-transform: uppercase;">
            ${hs.hotspot_level} HOTSPOT (${hs.hotspot_score}/100)
          </div>
          <div style="font-size: 13px; font-weight: bold; margin-top: 2px;">
            ${hs.name}
          </div>
          <div style="font-size: 11px; color: #475569; margin-top: 4px; line-height: 1.4;">
            <strong>${hs.incident_count} Incidents</strong> &bull; <strong>${hs.report_count} Reports</strong><br/>
            Dominant: ${hs.dominant_category.replace('_', ' ')}<br/>
            Avg Priority: ${hs.average_priority_score}/100
          </div>
        </div>
      `;

      circle.bindPopup(popupContent);
      circle.on('click', () => {
        setActiveHotspot(hs);
        if (onSelectHotspot) onSelectHotspot(hs);
      });
    });

    // 2. Render Individual Incident Markers
    incidents.forEach(inc => {
      if (!inc.latitude || !inc.longitude) return;

      const isSelected = selectedIncidentId === inc.id;
      let pinColor = '#0284c7'; // Sky blue
      if (inc.priority_level === 'P1_CRITICAL' || inc.priority_score >= 80) pinColor = '#dc2626'; // Red
      else if (inc.priority_level === 'P2_HIGH' || inc.priority_score >= 65) pinColor = '#ea580c'; // Orange

      const customIcon = L.divIcon({
        className: 'custom-leaflet-marker',
        html: `
          <div style="
            background-color: ${pinColor};
            width: ${isSelected ? '22px' : '16px'};
            height: ${isSelected ? '22px' : '16px'};
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.4);
            cursor: pointer;
            transition: transform 0.2s;
          "></div>
        `,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });

      const marker = L.marker([inc.latitude, inc.longitude], { icon: customIcon }).addTo(map);

      const markerPopup = `
        <div style="font-family: sans-serif; min-width: 180px;">
          <div style="font-size: 10px; font-weight: bold; color: ${pinColor}; uppercase;">
            ${inc.category.replace('_', ' ')} &bull; ${inc.priority_level || 'P3'} (${inc.priority_score}/100)
          </div>
          <div style="font-size: 12px; font-weight: bold; margin-top: 2px;">
            ${inc.title}
          </div>
          <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
            Dept: ${inc.assigned_department || 'Unassigned'}
          </div>
          <a href="/incident/${inc.id}" style="display: inline-block; margin-top: 6px; font-size: 11px; color: #0284c7; font-weight: bold; text-decoration: none;">
            View Incident Details &rarr;
          </a>
        </div>
      `;

      marker.bindPopup(markerPopup);
      marker.on('click', () => {
        setActiveIncident(inc);
        if (onSelectIncident) onSelectIncident(inc.id);
      });
    });

    if (allCoords.length > 1) {
      map.fitBounds(allCoords, { padding: [30, 30] });
    }

  }, [mapLoaded, incidents, hotspots, selectedIncidentId, selectedHotspotId]);

  return (
    <div className={`relative bg-slate-100 ${className}`}>
      <div ref={mapRef} className="w-full h-full z-10" />

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur text-white text-[10px] p-2.5 rounded-xl border border-slate-800 shadow-lg z-20 space-y-1">
        <div className="font-bold text-slate-300 flex items-center gap-1 mb-1">
          <Layers className="w-3 h-3 text-sky-400" /> Legend
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-600 border border-white inline-block"></span>
          <span>P1 Incident / Critical Hotspot</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-orange-500 border border-white inline-block"></span>
          <span>P2 Incident / High Hotspot</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-sky-500 border border-white inline-block"></span>
          <span>P3/P4 Incident</span>
        </div>
        <div className="flex items-center gap-2 pt-1 border-t border-slate-800">
          <span className="w-3 h-3 rounded-full bg-red-500/30 border border-red-500 inline-block"></span>
          <span>Hotspot Radius (250m)</span>
        </div>
      </div>
    </div>
  );
}
