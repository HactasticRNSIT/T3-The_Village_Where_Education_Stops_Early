/**
 * BaseMap.jsx
 * SafeRoute AI — Reusable Leaflet base map centered on Yadagiri, Telangana.
 * Accepts children as props so all overlay layers compose on top.
 *
 * Props:
 *   center     [lat, lon]   default: [16.7648, 77.1268]
 *   zoom       number       default: 13
 *   style      object       container style overrides
 *   className  string
 *   children   ReactNode    overlay layers (BoundaryCircle, SchoolMarkers, etc.)
 */

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const YADAGIRI = [16.7648, 77.1268];

const OSM_TILE = {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
};

// Dark-style tile for lawmaker dashboard (optional variant)
const CARTO_DARK_TILE = {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20,
};

export const MapContext = React.createContext(null);

export default function BaseMap({
    center = YADAGIRI,
    zoom = 13,
    tileVariant = 'osm', // 'osm' | 'dark'
    style = {},
    className = '',
    children,
    onMapReady,
}) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const [mapInstance, setMapInstance] = React.useState(null);

    useEffect(() => {
        if (mapRef.current) return; // already initialised

        const map = L.map(containerRef.current, {
            center,
            zoom,
            zoomControl: true,
            attributionControl: true,
        });

        const tile = tileVariant === 'dark' ? CARTO_DARK_TILE : OSM_TILE;
        L.tileLayer(tile.url, {
            attribution: tile.attribution,
            maxZoom: 19,
            subdomains: tile.subdomains || 'abc',
        }).addTo(map);

        // Custom zoom-control position (top-left)
        map.zoomControl.setPosition('topleft');

        mapRef.current = map;
        setMapInstance(map);
        onMapReady && onMapReady(map);

        return () => {
            map.remove();
            mapRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Keep center/zoom in sync if parent changes them
    useEffect(() => {
        if (!mapRef.current) return;
        mapRef.current.setView(center, zoom);
    }, [center, zoom]);

    const containerStyle = {
        width: '100%',
        height: '100%',
        minHeight: 400,
        position: 'relative',
        borderRadius: 12,
        overflow: 'hidden',
        ...style,
    };

    return (
        <MapContext.Provider value={mapInstance}>
            <div ref={containerRef} className={className} style={containerStyle} />
            {/* Children render after map is ready */}
            {mapInstance && children}
        </MapContext.Provider>
    );
}
