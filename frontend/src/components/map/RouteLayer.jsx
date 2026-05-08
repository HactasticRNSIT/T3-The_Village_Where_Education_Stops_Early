/**
 * RouteLayer.jsx
 * SafeRoute AI — Draws multiple routes to a selected school.
 * Colour-codes by safety score. Recommended route pulses.
 *
 * Props:
 *   routes   Route[]   list of route objects (see shape below)
 *
 * Route shape:
 *   {
 *     id          string
 *     latlngs     [lat, lon][]   ordered coordinate pairs
 *     safetyScore number         0–1
 *     isRecommended boolean
 *     topRiskFactor string       e.g. "Poor lighting"
 *     distanceKm  number
 *     minutesWalk number
 *   }
 */

import { useContext, useEffect, useRef } from 'react';
import L from 'leaflet';
import { MapContext } from './BaseMap';

const scoreColour = (score) => {
    if (score > 0.7) return '#22c55e';   // green — safe
    if (score >= 0.4) return '#f0962a';  // amber — moderate
    return '#e84545';                    // red — dangerous
};

const scoreLabel = (score) => {
    if (score > 0.7) return 'Safe';
    if (score >= 0.4) return 'Moderate';
    return 'High risk';
};

// Inject pulse CSS once
let pulseInjected = false;
const injectPulseCSS = () => {
    if (pulseInjected) return;
    pulseInjected = true;
    const style = document.createElement('style');
    style.textContent = `
    @keyframes sr-pulse {
      0%   { opacity: 1; }
      50%  { opacity: 0.45; }
      100% { opacity: 1; }
    }
    .sr-route-recommended {
      animation: sr-pulse 2s ease-in-out infinite;
    }
  `;
    document.head.appendChild(style);
};

export default function RouteLayer({ routes = [] }) {
    const map = useContext(MapContext);
    const layersRef = useRef([]);

    useEffect(() => {
        if (!map) return;
        injectPulseCSS();

        // Clear previous layers
        layersRef.current.forEach((l) => l.remove());
        layersRef.current = [];

        // Sort: draw low-safety routes first so recommended sits on top
        const sorted = [...routes].sort((a, b) => {
            if (a.isRecommended) return 1;
            if (b.isRecommended) return -1;
            return a.safetyScore - b.safetyScore;
        });

        sorted.forEach((route) => {
            const colour = scoreColour(route.safetyScore);
            const isRec = route.isRecommended;

            // Ghost/shadow line for recommended route (glow effect without CSS filters)
            if (isRec) {
                const shadow = L.polyline(route.latlngs, {
                    color: colour,
                    weight: 12,
                    opacity: 0.15,
                    interactive: false,
                }).addTo(map);
                layersRef.current.push(shadow);
            }

            // Main route line
            const polyline = L.polyline(route.latlngs, {
                color: colour,
                weight: isRec ? 5 : 3,
                opacity: isRec ? 0.95 : 0.65,
                dashArray: isRec ? null : '8 5',
                className: isRec ? 'sr-route-recommended' : '',
                lineCap: 'round',
                lineJoin: 'round',
            }).addTo(map);

            // Hover tooltip
            const tooltipHtml = `
        <div style="font-family:'DM Sans',sans-serif;padding:2px 4px;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span style="
              background:${colour}22;border:1.5px solid ${colour};
              color:${colour};font-size:10px;font-weight:700;
              padding:1px 7px;border-radius:99px;
            ">${scoreLabel(route.safetyScore).toUpperCase()}</span>
            <span style="font-size:12px;font-weight:600;color:#111;">
              Score: ${(route.safetyScore * 100).toFixed(0)}%
            </span>
          </div>
          <div style="font-size:11px;color:#6b7280;">
            ⚠ Top risk: <strong>${route.topRiskFactor}</strong>
          </div>
          ${route.distanceKm != null
                    ? `<div style="font-size:11px;color:#6b7280;margin-top:2px;">
                 ${route.distanceKm} km · ~${route.minutesWalk} min walk
               </div>`
                    : ''}
          ${isRec
                    ? `<div style="font-size:10px;color:${colour};font-weight:700;margin-top:4px;">
                 ★ Recommended route
               </div>`
                    : ''}
        </div>`;

            polyline.bindTooltip(tooltipHtml, {
                sticky: true,
                direction: 'top',
                offset: [0, -8],
                className: 'sr-route-tooltip',
            });

            layersRef.current.push(polyline);
        });

        return () => {
            layersRef.current.forEach((l) => l.remove());
            layersRef.current = [];
        };
    }, [map, routes]);

    return null;
}
