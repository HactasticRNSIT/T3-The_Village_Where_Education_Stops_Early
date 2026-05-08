/**
 * InfrastructureGapLayer.jsx
 * SafeRoute AI — Lawmaker dashboard overlay for infrastructure gaps.
 *   • Roads with no bus stops → red dashed polylines
 *   • Mobile dead zones → signal-off icon markers
 *   • Unlit road segments → moon icon markers
 *
 * Props:
 *   noBusRoutes   GapSegment[]    road segments without bus stops
 *   deadZones     PointFeature[]  locations with no mobile coverage
 *   unlitSegments GapSegment[]    road segments with no streetlighting
 *   visible       boolean         master toggle (default: true)
 *
 * GapSegment shape:  { id, latlngs: [lat,lon][], label? }
 * PointFeature shape: { id, lat, lon, label? }
 */

import { useContext, useEffect, useRef } from 'react';
import L from 'leaflet';
import { MapContext } from './BaseMap';

/* ── SVG icon factories ─────────────────────────────────────── */

const signalOffIcon = (label) =>
    L.divIcon({
        className: '',
        html: `
      <div title="${label || 'No mobile coverage'}" style="
        display:flex;flex-direction:column;align-items:center;gap:2px;
      ">
        <div style="
          background:#7c3aed;border-radius:50%;width:28px;height:28px;
          display:flex;align-items:center;justify-content:center;
          box-shadow:0 2px 6px rgba(124,58,237,0.45);
          border:2px solid #fff;
        ">
          <!-- Signal-off icon (3 bars with X) -->
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="#fff" stroke-width="2.2" stroke-linecap="round">
            <line x1="1" y1="1" x2="23" y2="23"/>
            <path d="M16.72 11.06A10.94 10.94 0 0119 12.55"/>
            <path d="M5 12.55a10.94 10.94 0 015.17-2.39"/>
            <path d="M10.71 5.05A16 16 0 0122.56 9"/>
            <path d="M1.42 9a15.91 15.91 0 014.7-2.88"/>
            <path d="M8.53 16.11a6 6 0 016.95 0"/>
            <line x1="12" y1="20" x2="12.01" y2="20"/>
          </svg>
        </div>
        ${label
                ? `<div style="font-size:9px;font-weight:600;color:#7c3aed;
                         background:rgba(255,255,255,0.9);padding:1px 4px;
                         border-radius:4px;white-space:nowrap;">${label}</div>`
                : ''}
      </div>`,
        iconSize: [28, label ? 44 : 30],
        iconAnchor: [14, label ? 44 : 30],
    });

const moonIcon = (label) =>
    L.divIcon({
        className: '',
        html: `
      <div title="${label || 'Unlit segment'}" style="
        display:flex;flex-direction:column;align-items:center;gap:2px;
      ">
        <div style="
          background:#f59e0b;border-radius:50%;width:28px;height:28px;
          display:flex;align-items:center;justify-content:center;
          box-shadow:0 2px 6px rgba(245,158,11,0.5);
          border:2px solid #fff;
        ">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="#fff" stroke-width="2.2" stroke-linecap="round"
               stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
          </svg>
        </div>
        ${label
                ? `<div style="font-size:9px;font-weight:600;color:#b45309;
                         background:rgba(255,255,255,0.9);padding:1px 4px;
                         border-radius:4px;white-space:nowrap;">${label}</div>`
                : ''}
      </div>`,
        iconSize: [28, label ? 44 : 30],
        iconAnchor: [14, label ? 44 : 30],
    });

/* ── Component ──────────────────────────────────────────────── */

export default function InfrastructureGapLayer({
    noBusRoutes = [],
    deadZones = [],
    unlitSegments = [],
    visible = true,
}) {
    const map = useContext(MapContext);
    const layersRef = useRef([]);

    useEffect(() => {
        if (!map) return;

        // Clear previous
        layersRef.current.forEach((l) => l.remove());
        layersRef.current = [];

        if (!visible) return;

        // ── No-bus-stop road segments (red dashed polyline) ──────
        noBusRoutes.forEach((seg) => {
            const line = L.polyline(seg.latlngs, {
                color: '#E24B4A',
                weight: 4,
                opacity: 0.85,
                dashArray: '12 6',
                lineCap: 'round',
            }).addTo(map);

            if (seg.label) {
                line.bindTooltip(
                    `<div style="font-family:'DM Sans',sans-serif;font-size:11px;">
             <strong style="color:#E24B4A;">No bus stop</strong><br/>${seg.label}
           </div>`,
                    { sticky: true, className: 'sr-gap-tooltip' }
                );
            }

            layersRef.current.push(line);
        });

        // ── Mobile dead zones ────────────────────────────────────
        deadZones.forEach((pt) => {
            const marker = L.marker([pt.lat, pt.lon], {
                icon: signalOffIcon(pt.label),
                title: pt.label || 'No mobile coverage',
            }).addTo(map);

            marker.bindPopup(
                `<div style="font-family:'DM Sans',sans-serif;padding:4px;">
           <div style="font-weight:700;color:#7c3aed;margin-bottom:4px;">
             📵 Mobile Dead Zone
           </div>
           <div style="font-size:12px;color:#374151;">
             ${pt.label || 'No cellular coverage in this area.'}
           </div>
           <div style="font-size:11px;color:#9ca3af;margin-top:6px;">
             Children cannot call for help in emergencies.
           </div>
         </div>`,
                { maxWidth: 220 }
            );

            layersRef.current.push(marker);
        });

        // ── Unlit segments ───────────────────────────────────────
        unlitSegments.forEach((seg) => {
            // Draw the unlit road segment with amber overlay
            const line = L.polyline(seg.latlngs, {
                color: '#f59e0b',
                weight: 5,
                opacity: 0.6,
                dashArray: '6 4',
                lineCap: 'round',
            }).addTo(map);

            layersRef.current.push(line);

            // Place moon icon at midpoint of segment
            if (seg.latlngs && seg.latlngs.length > 0) {
                const midIdx = Math.floor(seg.latlngs.length / 2);
                const [mlat, mlon] = seg.latlngs[midIdx];
                const marker = L.marker([mlat, mlon], {
                    icon: moonIcon(null),
                    title: seg.label || 'Unlit road segment',
                }).addTo(map);

                marker.bindPopup(
                    `<div style="font-family:'DM Sans',sans-serif;padding:4px;">
             <div style="font-weight:700;color:#b45309;margin-bottom:4px;">
               🌙 Unlit Road Segment
             </div>
             <div style="font-size:12px;color:#374151;">
               ${seg.label || 'No streetlighting detected on this stretch.'}
             </div>
             <div style="font-size:11px;color:#9ca3af;margin-top:6px;">
               Increases risk for children travelling after dark.
             </div>
           </div>`,
                    { maxWidth: 220 }
                );

                layersRef.current.push(marker);
            }
        });

        return () => {
            layersRef.current.forEach((l) => l.remove());
            layersRef.current = [];
        };
    }, [map, noBusRoutes, deadZones, unlitSegments, visible]);

    return null;
}
