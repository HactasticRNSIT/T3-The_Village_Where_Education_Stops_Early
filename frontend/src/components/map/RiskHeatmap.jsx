/**
 * RiskHeatmap.jsx
 * SafeRoute AI — Heatmap of high-risk road segments using Leaflet.heat.
 * Intensity driven by combined crime + terrain + lighting score.
 *
 * Props:
 *   points     HeatPoint[]   array of heat points
 *   visible    boolean       toggle visibility (default: true)
 *   radius     number        heat blob radius px (default: 25)
 *   blur       number        blur px (default: 20)
 *   maxZoom    number        (default: 17)
 *
 * HeatPoint shape:
 *   { lat, lon, intensity }   intensity 0–1 (1 = maximum risk)
 *
 * NOTE: Leaflet.heat is loaded from CDN at runtime (unpkg).
 *       Ensure your HTML includes leaflet.js BEFORE this component renders.
 */

import { useContext, useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { MapContext } from './BaseMap';

const HEAT_CDN =
    'https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js';

let heatScriptLoaded = false;
const loadHeatPlugin = () =>
    new Promise((resolve, reject) => {
        if (heatScriptLoaded || window.L?.heatLayer) {
            heatScriptLoaded = true;
            return resolve();
        }
        const script = document.createElement('script');
        script.src = HEAT_CDN;
        script.onload = () => {
            heatScriptLoaded = true;
            resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
    });

export default function RiskHeatmap({
    points = [],
    visible = true,
    radius = 25,
    blur = 20,
    maxZoom = 17,
}) {
    const map = useContext(MapContext);
    const heatLayerRef = useRef(null);
    const [pluginReady, setPluginReady] = useState(heatScriptLoaded);

    // Load Leaflet.heat plugin asynchronously
    useEffect(() => {
        if (pluginReady) return;
        loadHeatPlugin()
            .then(() => setPluginReady(true))
            .catch((err) => console.error('Failed to load Leaflet.heat:', err));
    }, [pluginReady]);

    // Build / update the heat layer
    useEffect(() => {
        if (!map || !pluginReady) return;

        // Remove existing layer
        if (heatLayerRef.current) {
            heatLayerRef.current.remove();
            heatLayerRef.current = null;
        }

        if (!visible || points.length === 0) return;

        // Convert to [lat, lon, intensity] triples
        const heatData = points.map(({ lat, lon, intensity }) => [
            lat,
            lon,
            Math.min(1, Math.max(0, intensity)),
        ]);

        // Gradient: green → amber → red (matching SafeRoute score palette)
        const gradient = {
            0.0: '#22c55e',
            0.35: '#f0962a',
            0.65: '#e84545',
            1.0: '#991b1b',
        };

        heatLayerRef.current = window.L.heatLayer(heatData, {
            radius,
            blur,
            maxZoom,
            gradient,
            minOpacity: 0.35,
        }).addTo(map);

        return () => {
            heatLayerRef.current && heatLayerRef.current.remove();
            heatLayerRef.current = null;
        };
    }, [map, pluginReady, points, visible, radius, blur, maxZoom]);

    return null;
}
