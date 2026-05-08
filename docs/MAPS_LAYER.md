# SafeRoute AI — Maps Layer

Reusable Leaflet-based map components shared between the **Village UI** and **Lawmaker Dashboard**.  
All centred on Yadagiri, Telangana (16.7648°N, 77.1268°E).

---

## Components

| File | Purpose |
|------|---------|
| `BaseMap.jsx` | Leaflet map shell with OSM/Carto tiles. Provides `MapContext` for child layers. |
| `BoundaryCircle.jsx` | Animated dashed 7 km boundary circle |
| `SchoolMarkers.jsx` | Custom school-pin markers with rich stat popups |
| `RouteLayer.jsx` | Multi-route polylines coloured by safety score + pulse animation |
| `RiskHeatmap.jsx` | Leaflet.heat heatmap of crime/terrain/lighting risk |
| `InfrastructureGapLayer.jsx` | Lawmaker-only: no-bus-stop roads, dead zones, unlit segments |
| `MapLegend.jsx` | Responsive collapsible legend (bottom-right) |
| `index.js` | Barrel export |

---

## Usage

### Village UI
```jsx
import { BaseMap, BoundaryCircle, SchoolMarkers,
         RouteLayer, RiskHeatmap, MapLegend } from './components/maps';

<div style={{ position:'relative', width:'100%', height:'600px' }}>
  <BaseMap center={userLocation} zoom={13}>
    <BoundaryCircle center={userLocation} radius={7000} animate />
    <SchoolMarkers schools={schools} onAnalyse={handleAnalyse} />
    <RouteLayer routes={routesToSelectedSchool} />
    <RiskHeatmap points={heatPoints} />
  </BaseMap>
  <MapLegend mode="village" />
</div>
```

### Lawmaker Dashboard
```jsx
import { BaseMap, BoundaryCircle, SchoolMarkers,
         RiskHeatmap, InfrastructureGapLayer, MapLegend } from './components/maps';

<div style={{ position:'relative', width:'100%', height:'600px' }}>
  <BaseMap center={YADAGIRI} zoom={13} tileVariant="dark">
    <BoundaryCircle center={YADAGIRI} radius={7000} color="#7c3aed" />
    <SchoolMarkers schools={schools} />
    <RiskHeatmap points={heatPoints} />
    <InfrastructureGapLayer
      noBusRoutes={noBusRoutes}
      deadZones={deadZones}
      unlitSegments={unlitSegments}
    />
  </BaseMap>
  <MapLegend mode="lawmaker" />
</div>
```

---

## Data Shapes

### School
```ts
{
  id: string
  name: string
  lat: number
  lon: number
  enrollment: number
  girlsPercent: number   // 0–100
  boysPercent: number
  dropoutRate: number    // percentage
  distanceKm?: number
}
```

### Route
```ts
{
  id: string
  latlngs: [number, number][]   // ordered [lat, lon] pairs
  safetyScore: number           // 0–1
  isRecommended: boolean
  topRiskFactor: string
  distanceKm?: number
  minutesWalk?: number
}
```

### HeatPoint
```ts
{ lat: number; lon: number; intensity: number }   // intensity 0–1
```

### GapSegment (InfrastructureGapLayer)
```ts
{ id: string; latlngs: [number, number][]; label?: string }
```

### PointFeature (InfrastructureGapLayer)
```ts
{ id: string; lat: number; lon: number; label?: string }
```

---

## Route Safety Colour Scheme

| Score | Colour | Meaning |
|-------|--------|---------|
| > 0.7 | `#22c55e` (green) | Safe |
| 0.4–0.7 | `#f0962a` (amber) | Moderate risk |
| < 0.4 | `#e84545` (red) | High risk |

The recommended route is drawn with `weight: 5` and pulses with a CSS animation.

---

## Dependencies

- `leaflet` ^1.9.4 — map engine (free, no API key)
- `leaflet.heat` ^0.2.0 — heatmap plugin (loaded from CDN)
- `react` ^18 — component framework
- OpenStreetMap tiles — free, no key required
- CartoDB dark tiles (optional lawmaker view) — free, no key required

---

## Tablet Responsiveness

All components use `width: 100%` / `height: 100%` layout.  
The legend collapses via a toggle button on narrow viewports.  
Sidebar uses CSS `position: fixed` + transform on screens ≤ 700 px.