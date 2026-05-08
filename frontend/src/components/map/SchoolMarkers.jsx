/**
 * SchoolMarkers.jsx
 * SafeRoute AI — Custom school icon markers inside the boundary.
 * Click → popup with school stats + "Analyse routes" button.
 *
 * Props:
 *   schools        School[]   array of school objects (see shape below)
 *   onAnalyse      (school) => void   called when user clicks "Analyse routes"
 *   selectedId     string | null      highlights the selected school
 *
 * School shape:
 *   { id, name, lat, lon, enrollment, girlsPercent, boysPercent,
 *     dropoutRate, distanceKm }
 */

import { useContext, useEffect, useRef } from 'react';
import L from 'leaflet';
import { MapContext } from './BaseMap';

// SVG school icon — pencil-and-book silhouette
const buildSchoolIcon = (selected = false) => {
    const bg = selected ? '#185FA5' : '#ffffff';
    const stroke = selected ? '#185FA5' : '#378ADD';
    const iconColor = selected ? '#ffffff' : '#185FA5';
    const shadow = selected
        ? 'drop-shadow(0 2px 6px rgba(24,95,165,0.6))'
        : 'drop-shadow(0 1px 4px rgba(0,0,0,0.25))';

    const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="34" height="40" viewBox="0 0 34 40">
      <path d="M17 0C8.716 0 2 6.716 2 15c0 9.5 15 25 15 25S32 24.5 32 15C32 6.716 25.284 0 17 0z"
            fill="${bg}" stroke="${stroke}" stroke-width="2"/>
      <!-- Graduation cap icon -->
      <g transform="translate(9,7)" fill="${iconColor}">
        <rect x="2" y="8" width="12" height="7" rx="1"/>
        <polygon points="8,2 16,6 8,10 0,6"/>
        <line x1="14" y1="6" x2="14" y2="12" stroke="${iconColor}" stroke-width="1.5"
              stroke-linecap="round"/>
        <circle cx="14" cy="12.5" r="1.2"/>
      </g>
    </svg>`;

    return L.divIcon({
        className: '',
        html: `<div style="filter:${shadow}">${svg}</div>`,
        iconSize: [34, 40],
        iconAnchor: [17, 40],
        popupAnchor: [0, -42],
    });
};

const statRow = (label, value, colour = '#185FA5') => `
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:5px 0;border-bottom:0.5px solid #e5e7eb;">
    <span style="font-size:12px;color:#6b7280;">${label}</span>
    <span style="font-size:13px;font-weight:600;color:${colour};">${value}</span>
  </div>`;

const genderBar = (girlsPct) => {
    const boysPct = 100 - girlsPct;
    return `
    <div style="margin:8px 0 4px;">
      <div style="font-size:11px;color:#6b7280;margin-bottom:4px;">Gender ratio</div>
      <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;">
        <div style="width:${girlsPct}%;background:#D4537E;"></div>
        <div style="width:${boysPct}%;background:#378ADD;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:10px;
                  color:#6b7280;margin-top:3px;">
        <span>♀ ${girlsPct}%</span><span>♂ ${boysPct}%</span>
      </div>
    </div>`;
};

export default function SchoolMarkers({
    schools = [],
    onAnalyse,
    selectedId = null,
}) {
    const map = useContext(MapContext);
    const markersRef = useRef([]);

    useEffect(() => {
        if (!map) return;

        // Clear previous
        markersRef.current.forEach((m) => m.remove());
        markersRef.current = [];

        schools.forEach((school) => {
            const isSelected = school.id === selectedId;
            const marker = L.marker([school.lat, school.lon], {
                icon: buildSchoolIcon(isSelected),
                title: school.name,
            }).addTo(map);

            const dropoutColour =
                school.dropoutRate > 15
                    ? '#E24B4A'
                    : school.dropoutRate > 8
                        ? '#EF9F27'
                        : '#639922';

            const popupContent = `
        <div style="font-family:'DM Sans',sans-serif;min-width:220px;padding:4px 2px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
            <div style="background:#E6F1FB;border-radius:8px;padding:6px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                   stroke="#185FA5" stroke-width="2" stroke-linecap="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
            </div>
            <div>
              <div style="font-size:14px;font-weight:700;color:#111827;line-height:1.2;">
                ${school.name}
              </div>
              ${school.distanceKm != null
                    ? `<div style="font-size:11px;color:#9ca3af;">${school.distanceKm} km away</div>`
                    : ''}
            </div>
          </div>
          ${statRow('Enrollment', school.enrollment.toLocaleString())}
          ${statRow('Dropout rate', `${school.dropoutRate}%`, dropoutColour)}
          ${genderBar(school.girlsPercent)}
          <button
            onclick="window.__srAnalyse && window.__srAnalyse('${school.id}')"
            style="
              width:100%;margin-top:10px;padding:8px 0;
              background:#185FA5;color:#fff;border:none;border-radius:8px;
              font-size:13px;font-weight:600;cursor:pointer;
              font-family:'DM Sans',sans-serif;
              transition:background 0.15s;
            "
            onmouseover="this.style.background='#0C447C'"
            onmouseout="this.style.background='#185FA5'"
          >
            Analyse routes →
          </button>
        </div>`;

            marker.bindPopup(popupContent, {
                maxWidth: 260,
                className: 'sr-popup',
            });

            markersRef.current.push(marker);
        });

        // Bridge popup button → React callback via window global
        window.__srAnalyse = (id) => {
            const school = schools.find((s) => s.id === id);
            if (school && onAnalyse) onAnalyse(school);
        };

        return () => {
            markersRef.current.forEach((m) => m.remove());
            markersRef.current = [];
            delete window.__srAnalyse;
        };
    }, [map, schools, selectedId, onAnalyse]);

    return null;
}
