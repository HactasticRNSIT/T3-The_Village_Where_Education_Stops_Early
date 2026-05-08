/**
 * BoundaryCircle.jsx
 * SafeRoute AI — Animated dashed boundary circle around a given lat/lon.
 *
 * Props:
 *   center     [lat, lon]   centre of the circle
 *   radius     number       radius in metres (default: 7000 = 7 km)
 *   animate    boolean      triggers grow-in animation when true (default: false)
 *   color      string       stroke colour (default: '#378ADD')
 *   label      string       optional label shown near the circle edge
 */

import { useContext, useEffect, useRef } from 'react';
import L from 'leaflet';
import { MapContext } from './BaseMap';

const DEFAULT_OPTIONS = {
    radius: 7000,
    color: '#378ADD',
    fillColor: '#378ADD',
    fillOpacity: 0.04,
    weight: 2,
    dashArray: '10 8',
    dashOffset: '0',
    interactive: false,
};

export default function BoundaryCircle({
    center,
    radius = 7000,
    animate = false,
    color = '#378ADD',
    label,
}) {
    const map = useContext(MapContext);
    const circleRef = useRef(null);
    const labelRef = useRef(null);
    const rafRef = useRef(null);

    useEffect(() => {
        if (!map || !center) return;

        // Start at radius=1 and animate to target if animate=true
        const startRadius = animate ? 1 : radius;

        const circle = L.circle(center, {
            ...DEFAULT_OPTIONS,
            radius: startRadius,
            color,
            fillColor: color,
        }).addTo(map);

        circleRef.current = circle;

        if (animate) {
            const startTime = performance.now();
            const duration = 900; // ms

            const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

            const step = (now) => {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const eased = easeOutCubic(progress);
                circle.setRadius(eased * radius);

                if (progress < 1) {
                    rafRef.current = requestAnimationFrame(step);
                }
            };

            rafRef.current = requestAnimationFrame(step);
        }

        // Animated dash offset (rotating dashes)
        let offset = 0;
        const dashAnim = setInterval(() => {
            offset = (offset + 1) % 18;
            circle.setStyle({ dashOffset: `${offset}` });
        }, 60);

        // Optional label marker near the top of the circle
        if (label) {
            const labelLatLng = L.latLng(
                center[0] + (radius / 111000) * 1.02,
                center[1]
            );
            const labelIcon = L.divIcon({
                className: '',
                html: `<div style="
          background: rgba(55,138,221,0.9);
          color: #fff;
          font-size: 11px;
          font-family: 'DM Sans', sans-serif;
          font-weight: 600;
          padding: 3px 8px;
          border-radius: 99px;
          white-space: nowrap;
          letter-spacing: 0.03em;
          box-shadow: 0 1px 4px rgba(0,0,0,0.2);
        ">${label}</div>`,
                iconAnchor: [0, 0],
            });
            labelRef.current = L.marker(labelLatLng, {
                icon: labelIcon,
                interactive: false,
            }).addTo(map);
        }

        return () => {
            cancelAnimationFrame(rafRef.current);
            clearInterval(dashAnim);
            circle.remove();
            labelRef.current && labelRef.current.remove();
        };
    }, [map, center, radius, animate, color, label]);

    return null;
}
