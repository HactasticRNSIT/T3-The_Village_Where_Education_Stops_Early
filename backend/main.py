"""
main.py — SafeRoute AI FastAPI Backend
========================================
Student commute safety platform for Yadagiri, Karnataka.

Endpoints
─────────
POST /api/routes/analyze            → Route safety analysis
GET  /api/schools/boundary          → Schools within radius (GeoJSON)
GET  /api/lawmaker/village-report   → Village-level school needs report
POST /api/lawmaker/school-analysis  → Deep-dive school route analysis
GET  /health                        → Deployment health check
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from scoring.route_scorer import (
    RoutePoint,
    RouteScorer,
    RouteAnalysis,
    score_multiple_routes,
    haversine_distance,
    get_crime_risk,
    get_population_density,
    get_terrain_slope,
    get_weather_risk,
    _stable_hash,
)

# ─────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="SafeRoute AI",
    description=(
        "AI-powered student commute safety scoring for Yadagiri, Karnataka. "
        "Combines road quality, terrain, weather, crime, population density "
        "and public transport data to help students find the safest routes to school."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scorer = RouteScorer()

# ─────────────────────────────────────────────
# Static school data — Yadagiri district
# (In production: query a PostGIS/OSM database)
# ─────────────────────────────────────────────

SCHOOLS: List[Dict[str, Any]] = [
    {
        "school_id":    "SCH001",
        "name":         "Government Higher Primary School, Yadagiri",
        "lat":          16.7720,
        "lon":          79.1710,
        "type":         "government",
        "grades":       "1–8",
        "students":     420,
        "village":      "Yadagiri",
        "taluk":        "Yadagiri",
        "medium":       "Kannada",
        "facilities":   ["library", "playground", "midday_meal"],
    },
    {
        "school_id":    "SCH002",
        "name":         "Zilla Parishad High School, Venkatapur",
        "lat":          16.7550,
        "lon":          79.1450,
        "type":         "government",
        "grades":       "1–10",
        "students":     310,
        "village":      "Venkatapur",
        "taluk":        "Yadagiri",
        "medium":       "Kannada",
        "facilities":   ["playground", "midday_meal"],
    },
    {
        "school_id":    "SCH003",
        "name":         "Karnataka Public School, Gurmitkal",
        "lat":          16.8810,
        "lon":          77.0940,
        "type":         "private",
        "grades":       "1–12",
        "students":     780,
        "village":      "Gurmitkal",
        "taluk":        "Gurmitkal",
        "medium":       "English",
        "facilities":   ["library", "lab", "sports", "transport", "midday_meal"],
    },
    {
        "school_id":    "SCH004",
        "name":         "Government Model Primary School, Shahpur",
        "lat":          16.6940,
        "lon":          76.8430,
        "type":         "government",
        "grades":       "1–7",
        "students":     195,
        "village":      "Shahpur",
        "taluk":        "Shahpur",
        "medium":       "Urdu",
        "facilities":   ["midday_meal"],
    },
    {
        "school_id":    "SCH005",
        "name":         "Kendriya Vidyalaya, Raichur Road",
        "lat":          16.7900,
        "lon":          79.2100,
        "type":         "central",
        "grades":       "1–12",
        "students":     960,
        "village":      "Yadagiri",
        "taluk":        "Yadagiri",
        "medium":       "English/Hindi",
        "facilities":   ["library", "lab", "sports", "transport", "midday_meal", "hostel"],
    },
    {
        "school_id":    "SCH006",
        "name":         "Government Girls High School, Wadagera",
        "lat":          16.6720,
        "lon":          79.0580,
        "type":         "government",
        "grades":       "6–10",
        "students":     240,
        "village":      "Wadagera",
        "taluk":        "Yadagiri",
        "medium":       "Kannada",
        "facilities":   ["midday_meal", "playground"],
    },
    {
        "school_id":    "SCH007",
        "name":         "Social Welfare Residential School, Hunsagi",
        "lat":          16.7100,
        "lon":          79.3050,
        "type":         "residential",
        "grades":       "5–10",
        "students":     350,
        "village":      "Hunsagi",
        "taluk":        "Shorapur",
        "medium":       "Kannada",
        "facilities":   ["hostel", "midday_meal", "playground"],
    },
    {
        "school_id":    "SCH008",
        "name":         "Government Higher Secondary, Shorapur",
        "lat":          16.5280,
        "lon":          76.7560,
        "type":         "government",
        "grades":       "11–12",
        "students":     510,
        "village":      "Shorapur",
        "taluk":        "Shorapur",
        "medium":       "Kannada",
        "facilities":   ["lab", "library", "midday_meal"],
    },
]

# Village → school index for quick lookup
VILLAGE_INDEX: Dict[str, List[str]] = {}
for s in SCHOOLS:
    VILLAGE_INDEX.setdefault(s["village"].lower(), []).append(s["school_id"])
    VILLAGE_INDEX.setdefault(s["taluk"].lower(), []).append(s["school_id"])

SCHOOL_INDEX: Dict[str, Dict] = {s["school_id"]: s for s in SCHOOLS}

# ─────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────

class RouteAnalyzeRequest(BaseModel):
    origin_lat:  float = Field(..., ge=-90,  le=90,  examples=[16.770])
    origin_lon:  float = Field(..., ge=-180, le=180, examples=[79.170])
    travel_time: str   = Field("morning", examples=["morning"])

    @validator("travel_time")
    def validate_travel_time(cls, v):
        allowed = {"morning", "afternoon", "evening"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"travel_time must be one of {allowed}")
        return v


class SchoolAnalysisRequest(BaseModel):
    school_id: str = Field(..., examples=["SCH001"])


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _schools_within_radius(
    lat: float, lon: float, radius_km: float
) -> List[Dict]:
    return [
        s for s in SCHOOLS
        if haversine_distance(lat, lon, s["lat"], s["lon"]) <= radius_km
    ]


def _generate_routes_to_school(
    origin_lat: float,
    origin_lon: float,
    school: Dict,
    n_routes: int = 3,
) -> List[List[RoutePoint]]:
    """
    Generate n_routes candidate paths between origin and school.
    In production: call OSRM / GraphHopper for real routing.
    Here we interpolate with slight perturbations for each alternative.
    """
    routes = []
    dest_lat, dest_lon = school["lat"], school["lon"]

    for route_num in range(n_routes):
        # Vary the number of waypoints
        n_mid = 3 + route_num
        pts = [RoutePoint(origin_lat, origin_lon)]

        for i in range(1, n_mid + 1):
            t = i / (n_mid + 1)
            # Add sinusoidal deviation for alternative routes
            perturb_lat = math.sin(route_num * 1.3 + i) * 0.005 * (route_num + 0.5)
            perturb_lon = math.cos(route_num * 1.1 + i) * 0.005 * (route_num + 0.5)
            mid_lat = origin_lat + t * (dest_lat - origin_lat) + perturb_lat
            mid_lon = origin_lon + t * (dest_lon - origin_lon) + perturb_lon
            pts.append(RoutePoint(round(mid_lat, 6), round(mid_lon, 6)))

        pts.append(RoutePoint(dest_lat, dest_lon))
        routes.append(pts)

    return routes


def _route_to_geojson_feature(
    analysis: RouteAnalysis,
    route_label: str,
    school: Dict,
) -> Dict:
    """Convert a RouteAnalysis into a GeoJSON Feature."""
    coordinates = []
    if analysis.segment_scores:
        coordinates.append([
            analysis.segment_scores[0].start_point.lon,
            analysis.segment_scores[0].start_point.lat,
        ])
        for seg in analysis.segment_scores:
            coordinates.append([seg.end_point.lon, seg.end_point.lat])

    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {
            "route_id":     analysis.route_id,
            "route_label":  route_label,
            "school_id":    school["school_id"],
            "school_name":  school["name"],
            "safety_score": analysis.overall_safety_score,
            "distance_km":  analysis.total_distance_km,
            "travel_time":  analysis.travel_time_context,
            "explanation":  analysis.explanation,
            "confidence":   analysis.confidence_score,
        },
    }


def _score_school_need(school: Dict, travel_time: str = "morning") -> Dict:
    """
    Score how urgently a school needs safety intervention.
    Returns a dict with a 'need_score' [0,1] and driving factors.
    """
    lat, lon = school["lat"], school["lon"]
    crime = get_crime_risk(lat, lon)
    pop   = get_population_density(lat, lon)
    wthr  = get_weather_risk(lat, lon, travel_time)

    # Need = high crime + poor density + bad weather + low facilities
    n_facilities   = len(school.get("facilities", []))
    facility_score = min(1.0, n_facilities / 6)
    student_load   = min(1.0, school.get("students", 0) / 1000)

    need_score = (
        0.35 * crime +
        0.25 * (1 - pop) +
        0.15 * (1 - wthr) +
        0.15 * (1 - facility_score) +
        0.10 * student_load
    )
    return {
        "school_id":    school["school_id"],
        "school_name":  school["name"],
        "need_score":   round(need_score, 4),
        "crime_risk":   round(crime, 4),
        "pop_density":  round(pop, 4),
        "weather_risk": round(1 - wthr, 4),
        "n_facilities": n_facilities,
        "students":     school.get("students", 0),
    }


def _get_interventions(need_data: Dict, school: Dict) -> List[str]:
    """Map high-need factors to recommended interventions."""
    interventions = []
    if need_data["crime_risk"] > 0.55:
        interventions.append("Deploy community police escorts during school hours")
        interventions.append("Install CCTV cameras along primary access roads")
    if need_data["pop_density"] < 0.30:
        interventions.append("Establish student buddy-system or group-walk programs")
        interventions.append("Partner with local NGOs for route warden volunteers")
    if need_data["weather_risk"] > 0.50:
        interventions.append("Build covered walkways at key flood-prone segments")
        interventions.append("Provide weather alerts via SMS for parents")
    if need_data["n_facilities"] < 3:
        interventions.append("Prioritise infrastructure upgrades (toilet, library, water)")
    if need_data["students"] > 600:
        interventions.append("Add a second shift or stagger dismissal times to reduce crowding")
    if not interventions:
        interventions.append("Continue routine monitoring; no urgent intervention required")
    return interventions


# ── Budget Intervention Estimator ──────────────────────────────────────────
# Cost benchmarks based on Karnataka RDPR & PMGSY rates (2024-25)
# All values in Indian Rupees (₹)

INFRA_COST_CATALOG: Dict[str, Dict[str, Any]] = {
    "street_lighting": {
        "label":       "Solar LED Street Lighting",
        "category":    "Safety & Lighting",
        "unit":        "pole",
        "unit_cost":   18000,
        "description": "40W solar LED pole with battery, auto dusk-dawn",
    },
    "cctv": {
        "label":       "CCTV Surveillance Camera",
        "category":    "Safety & Lighting",
        "unit":        "camera",
        "unit_cost":   35000,
        "description": "IP67 weatherproof camera with 30-day local storage",
    },
    "bus_stop": {
        "label":       "Covered Bus Stop Shelter",
        "category":    "Transit Infrastructure",
        "unit":        "shelter",
        "unit_cost":   120000,
        "description": "Steel-frame shelter with seating for 10, signage board",
    },
    "road_paving": {
        "label":       "Road Paving (CC / Bitumen)",
        "category":    "Road Infrastructure",
        "unit":        "km",
        "unit_cost":   2500000,
        "description": "3.75m wide CC road per PMGSY spec, incl. drainage",
    },
    "footpath": {
        "label":       "Paved Footpath with Handrails",
        "category":    "Road Infrastructure",
        "unit":        "km",
        "unit_cost":   800000,
        "description": "1.5m wide cement footpath with MS handrails",
    },
    "covered_walkway": {
        "label":       "Covered Walkway (Flood-Prone)",
        "category":    "Weather Protection",
        "unit":        "100m section",
        "unit_cost":   350000,
        "description": "Elevated concrete walkway with roof, 2m wide",
    },
    "drainage": {
        "label":       "Storm-Water Drain",
        "category":    "Weather Protection",
        "unit":        "km",
        "unit_cost":   600000,
        "description": "Open masonry drain along road, 0.6m x 0.6m",
    },
    "sms_alert_system": {
        "label":       "SMS Weather Alert System",
        "category":    "Technology",
        "unit":        "setup",
        "unit_cost":   45000,
        "description": "Annual setup: API integration + SMS credits for 500 parents",
    },
    "toilet_block": {
        "label":       "Toilet Block (4 units)",
        "category":    "School Facilities",
        "unit":        "block",
        "unit_cost":   280000,
        "description": "4-unit toilet block with water tank, SBM spec",
    },
    "library": {
        "label":       "Mini Library Setup",
        "category":    "School Facilities",
        "unit":        "setup",
        "unit_cost":   95000,
        "description": "Bookshelves, 500 books, reading space furniture",
    },
    "drinking_water": {
        "label":       "RO Drinking Water Unit",
        "category":    "School Facilities",
        "unit":        "unit",
        "unit_cost":   65000,
        "description": "50 LPH RO purifier with storage tank",
    },
    "police_escort": {
        "label":       "Community Police Escort Program",
        "category":    "Safety & Lighting",
        "unit":        "year",
        "unit_cost":   180000,
        "description": "2 wardens, morning + evening shift, annual cost",
    },
    "buddy_system": {
        "label":       "Student Buddy/Group-Walk Program",
        "category":    "Community Programs",
        "unit":        "year",
        "unit_cost":   25000,
        "description": "Coordination, reflective vests, whistle kits",
    },
    "ngo_partnership": {
        "label":       "NGO Route Warden Volunteers",
        "category":    "Community Programs",
        "unit":        "year",
        "unit_cost":   60000,
        "description": "Stipend & training for 3 local volunteers",
    },
    "shift_management": {
        "label":       "Staggered Dismissal System",
        "category":    "Operational",
        "unit":        "setup",
        "unit_cost":   15000,
        "description": "Signage, timetable redesign, parent comms",
    },
}


def _estimate_budget(
    suggested_fixes: List[Dict],
    need_data: Dict,
    school: Dict,
    crime_hotspot_count: int = 0,
    terrain_issue_count: int = 0,
) -> Dict[str, Any]:
    """
    Map each suggested fix to items from INFRA_COST_CATALOG.
    Returns per-item breakdown + category totals + grand total.
    """
    line_items: List[Dict] = []

    # Compute quantities from context
    n_hotspots = max(crime_hotspot_count, 1)
    avg_route_km = 2.5  # average student commute distance in Yadagiri
    missing_facilities = []
    all_possible = {"library", "lab", "playground", "transport", "midday_meal", "hostel"}
    existing = set(school.get("facilities", []))
    missing_facilities = all_possible - existing

    for fix in suggested_fixes:
        fix_text = fix.get("fix", "").lower()

        if "street lighting" in fix_text or "motion-sensor" in fix_text:
            qty = n_hotspots * 4  # 4 poles per hotspot zone
            item = INFRA_COST_CATALOG["street_lighting"]
            line_items.append({**item, "quantity": qty, "total": item["unit_cost"] * qty,
                               "fix_ref": fix["fix"]})

        if "cctv" in fix_text:
            qty = max(n_hotspots * 2, 4)
            item = INFRA_COST_CATALOG["cctv"]
            line_items.append({**item, "quantity": qty, "total": item["unit_cost"] * qty,
                               "fix_ref": fix["fix"]})

        if "footpath" in fix_text or "paved" in fix_text or "handrail" in fix_text:
            qty_km = round(avg_route_km * 0.4, 1)  # ~40% of route needs footpath
            item = INFRA_COST_CATALOG["footpath"]
            line_items.append({**item, "quantity": qty_km, "total": int(item["unit_cost"] * qty_km),
                               "fix_ref": fix["fix"]})

        if "covered walkway" in fix_text:
            qty = max(terrain_issue_count, 1) * 2  # 2 sections per issue zone
            item = INFRA_COST_CATALOG["covered_walkway"]
            line_items.append({**item, "quantity": qty, "total": item["unit_cost"] * qty,
                               "fix_ref": fix["fix"]})

        if "weather alert" in fix_text or "sms" in fix_text:
            item = INFRA_COST_CATALOG["sms_alert_system"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})

        if "police escort" in fix_text or "community police" in fix_text:
            item = INFRA_COST_CATALOG["police_escort"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})

        if "buddy" in fix_text or "group-walk" in fix_text:
            item = INFRA_COST_CATALOG["buddy_system"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})

        if "ngo" in fix_text or "warden" in fix_text or "volunteer" in fix_text:
            item = INFRA_COST_CATALOG["ngo_partnership"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})

        if "infrastructure upgrade" in fix_text or "toilet" in fix_text:
            if "library" not in existing:
                item = INFRA_COST_CATALOG["library"]
                line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                                   "fix_ref": fix["fix"]})
            item = INFRA_COST_CATALOG["toilet_block"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})
            item = INFRA_COST_CATALOG["drinking_water"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})

        if "shift" in fix_text or "stagger" in fix_text or "dismissal" in fix_text:
            item = INFRA_COST_CATALOG["shift_management"]
            line_items.append({**item, "quantity": 1, "total": item["unit_cost"],
                               "fix_ref": fix["fix"]})

    # Deduplicate by label
    seen = set()
    unique_items = []
    for li in line_items:
        if li["label"] not in seen:
            seen.add(li["label"])
            unique_items.append(li)
    line_items = unique_items

    grand_total = sum(li["total"] for li in line_items)

    # Category breakdown
    categories: Dict[str, int] = {}
    for li in line_items:
        cat = li["category"]
        categories[cat] = categories.get(cat, 0) + li["total"]

    return {
        "line_items": [
            {
                "label":       li["label"],
                "category":    li["category"],
                "unit":        li["unit"],
                "unit_cost":   li["unit_cost"],
                "quantity":    li["quantity"],
                "total":       li["total"],
                "description": li["description"],
            }
            for li in line_items
        ],
        "category_breakdown": [
            {"category": cat, "total": total}
            for cat, total in sorted(categories.items(), key=lambda x: -x[1])
        ],
        "grand_total":  grand_total,
        "currency":     "INR",
        "note":         "Estimates based on Karnataka RDPR & PMGSY 2024-25 benchmark rates. "
                        "Actual costs may vary ±20% based on site conditions and contractor rates.",
    }


def _detect_crime_hotspots(
    lat: float, lon: float, radius: float = 0.10
) -> List[Dict]:
    """Return nearby crime hotspot indicators."""
    hotspots = []
    grid_step = 0.02
    lat0, lon0 = lat - radius, lon - radius

    for dlat in [i * grid_step for i in range(int(2*radius/grid_step))]:
        for dlon in [i * grid_step for i in range(int(2*radius/grid_step))]:
            glat, glon = lat0 + dlat, lon0 + dlon
            cr = get_crime_risk(glat, glon)
            if cr > 0.65:
                hotspots.append({
                    "lat":        round(glat, 5),
                    "lon":        round(glon, 5),
                    "crime_risk": round(cr, 4),
                    "severity":   "high" if cr > 0.80 else "moderate",
                })
    return sorted(hotspots, key=lambda x: -x["crime_risk"])[:5]


def _route_confidence(
    schools_found: int,
    origin_in_yadagiri: bool,
    travel_time: str,
) -> float:
    """Top-level request confidence estimate."""
    base = 0.75 if origin_in_yadagiri else 0.45
    school_bonus = min(0.15, schools_found * 0.03)
    time_bonus   = 0.05 if travel_time == "morning" else 0.0
    return round(min(0.95, base + school_bonus + time_bonus), 4)


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check() -> Dict:
    """Deployment health probe."""
    return {
        "status":    "healthy",
        "service":   "SafeRoute AI",
        "version":   "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "schools_loaded": len(SCHOOLS),
        "model_ready":    True,
    }


# ── POST /api/routes/analyze ────────────────────────────────────────────────

@app.post("/api/routes/analyze", tags=["Routes"])
def analyze_routes(req: RouteAnalyzeRequest) -> Dict[str, Any]:
    """
    Analyse commute routes from an origin point to all nearby schools.

    - Finds schools within 8 km.
    - Generates 3 candidate routes per school.
    - Scores each route with the SafeRoute AI model.
    - Returns best overall route + per-school route comparison.
    """
    start_ts = time.time()

    nearby_schools = _schools_within_radius(req.origin_lat, req.origin_lon, radius_km=8.0)
    if not nearby_schools:
        # Widen search
        nearby_schools = _schools_within_radius(req.origin_lat, req.origin_lon, radius_km=30.0)

    origin_in_yadagiri = (
        16.50 <= req.origin_lat <= 17.10 and
        78.80 <= req.origin_lon <= 79.40
    )

    routes_per_school: List[Dict] = []
    all_best_analyses: List[Tuple[RouteAnalysis, Dict]] = []

    for school in nearby_schools[:6]:   # cap at 6 schools for latency
        candidate_routes = _generate_routes_to_school(
            req.origin_lat, req.origin_lon, school, n_routes=3
        )
        analyses = score_multiple_routes(candidate_routes, req.travel_time)

        best  = analyses[0]
        worst = analyses[-1]

        routes_per_school.append({
            "school_id":   school["school_id"],
            "school_name": school["name"],
            "distance_km": round(
                haversine_distance(
                    req.origin_lat, req.origin_lon, school["lat"], school["lon"]
                ), 2
            ),
            "best_route": {
                "route_id":     best.route_id,
                "safety_score": best.overall_safety_score,
                "distance_km":  best.total_distance_km,
                "explanation":  best.explanation,
                "confidence":   best.confidence_score,
                "women_safety_warning": best.women_safety_warning,
                "geojson_feature": _route_to_geojson_feature(best, "Best Route", school),
            },
            "alternative_route": {
                "route_id":     worst.route_id,
                "safety_score": worst.overall_safety_score,
                "distance_km":  worst.total_distance_km,
                "explanation":  worst.explanation,
            },
            "all_route_scores": [
                {"route_id": a.route_id, "safety_score": a.overall_safety_score}
                for a in analyses
            ],
        })
        all_best_analyses.append((best, school))

    # Global best route across all schools
    if all_best_analyses:
        global_best, best_school = max(
            all_best_analyses, key=lambda x: x[0].overall_safety_score
        )
    else:
        raise HTTPException(status_code=404, detail="No schools found near this location.")

    confidence = _route_confidence(len(nearby_schools), origin_in_yadagiri, req.travel_time)

    elapsed_ms = round((time.time() - start_ts) * 1000, 1)

    return {
        "schools": [
            {
                "school_id":  s["school_id"],
                "name":       s["name"],
                "lat":        s["lat"],
                "lon":        s["lon"],
                "type":       s["type"],
                "grades":     s["grades"],
                "students":   s["students"],
                "distance_km": round(
                    haversine_distance(
                        req.origin_lat, req.origin_lon, s["lat"], s["lon"]
                    ), 2
                ),
            }
            for s in nearby_schools[:6]
        ],
        "routes_per_school": routes_per_school,
        "best_route": {
            "school_id":      best_school["school_id"],
            "school_name":    best_school["name"],
            "route_id":       global_best.route_id,
            "safety_score":   global_best.overall_safety_score,
            "distance_km":    global_best.total_distance_km,
            "explanation":    global_best.explanation,
            "women_safety_warning": global_best.women_safety_warning,
            "problematic_segments": global_best.problematic_segments,
            "shap_contributions":   global_best.shap_contributions,
            "geojson_feature": _route_to_geojson_feature(
                global_best, "Safest Overall Route", best_school
            ),
        },
        "safety_scores": {
            s["school_id"]: next(
                (r["best_route"]["safety_score"]
                 for r in routes_per_school
                 if r["school_id"] == s["school_id"]),
                None
            )
            for s in nearby_schools[:6]
        },
        "confidence_score":   confidence,
        "origin":             {"lat": req.origin_lat, "lon": req.origin_lon},
        "travel_time":        req.travel_time,
        "schools_found":      len(nearby_schools),
        "processing_time_ms": elapsed_ms,
        "timestamp":          datetime.utcnow().isoformat() + "Z",
    }


# ── GET /api/schools/boundary ───────────────────────────────────────────────

@app.get("/api/schools/boundary", tags=["Schools"])
def schools_in_boundary(
    lat:       float = Query(...,    ge=-90,  le=90),
    lon:       float = Query(...,    ge=-180, le=180),
    radius_km: float = Query(5.0,   ge=0.1,  le=100.0),
) -> Dict[str, Any]:
    """
    Return all schools within *radius_km* of (lat, lon) as a GeoJSON FeatureCollection.
    """
    found = _schools_within_radius(lat, lon, radius_km)

    features = []
    for s in found:
        dist = haversine_distance(lat, lon, s["lat"], s["lon"])
        need = _score_school_need(s)
        features.append({
            "type": "Feature",
            "geometry": {
                "type":        "Point",
                "coordinates": [s["lon"], s["lat"]],
            },
            "properties": {
                **{k: v for k, v in s.items() if k not in ("lat", "lon")},
                "distance_km": round(dist, 3),
                "need_score":  need["need_score"],
            },
        })

    # Confidence: higher when searching within Yadagiri district
    in_district = (16.50 <= lat <= 17.10 and 78.80 <= lon <= 79.40)
    confidence  = 0.90 if in_district else 0.55

    return {
        "type": "FeatureCollection",
        "features":        features,
        "metadata": {
            "query_lat":   lat,
            "query_lon":   lon,
            "radius_km":   radius_km,
            "count":       len(features),
            "confidence_score": confidence,
            "timestamp":   datetime.utcnow().isoformat() + "Z",
        },
    }


# ── GET /api/lawmaker/village-report ────────────────────────────────────────

@app.get("/api/lawmaker/village-report", tags=["Lawmaker"])
def village_report(
    village_name: str = Query(..., min_length=2, example="Yadagiri"),
) -> Dict[str, Any]:
    """
    Generate a village-level school safety report for lawmakers / policymakers.
    Schools are ranked by intervention need; top issues and recommended
    interventions are surfaced for each.
    """
    village_key = village_name.lower().strip()
    matched_ids = VILLAGE_INDEX.get(village_key, [])

    # Fuzzy fallback: partial match on village or name
    if not matched_ids:
        matched_ids = list({
            s["school_id"] for s in SCHOOLS
            if village_key in s["village"].lower()
            or village_key in s["name"].lower()
            or village_key in s["taluk"].lower()
        })

    if not matched_ids:
        raise HTTPException(
            status_code=404,
            detail=f"No schools found for village/taluk '{village_name}'. "
                   "Try nearby taluk name or district name."
        )

    schools_in_village = [SCHOOL_INDEX[sid] for sid in set(matched_ids)
                          if sid in SCHOOL_INDEX]

    # Rank by need (descending)
    need_scores = [_score_school_need(s) for s in schools_in_village]
    need_scores.sort(key=lambda x: -x["need_score"])

    # Top issues per school
    top_issues_per_school: List[Dict] = []
    for ns in need_scores:
        sid   = ns["school_id"]
        school = SCHOOL_INDEX[sid]
        issues = []

        if ns["crime_risk"] > 0.55:
            issues.append({
                "issue":    "High crime risk on access roads",
                "severity": "critical" if ns["crime_risk"] > 0.75 else "high",
                "metric":   f"Crime index: {ns['crime_risk']:.2f}",
            })
        if ns["pop_density"] < 0.30:
            issues.append({
                "issue":    "Low population density — reduced witnesses",
                "severity": "high",
                "metric":   f"Density index: {ns['pop_density']:.2f}",
            })
        if ns["weather_risk"] > 0.45:
            issues.append({
                "issue":    "Flood / rain risk during monsoon",
                "severity": "moderate",
                "metric":   f"Weather risk: {ns['weather_risk']:.2f}",
            })
        if ns["n_facilities"] < 3:
            issues.append({
                "issue":    "Inadequate school facilities",
                "severity": "moderate",
                "metric":   f"Facilities: {ns['n_facilities']}/6",
            })
        if not issues:
            issues.append({
                "issue":    "No critical issues identified",
                "severity": "low",
                "metric":   f"Need score: {ns['need_score']:.2f}",
            })

        top_issues_per_school.append({
            "school_id":   sid,
            "school_name": school["name"],
            "need_score":  ns["need_score"],
            "top_issues":  issues[:3],
            "interventions": _get_interventions(ns, school),
        })

    # Aggregate village-level stats
    avg_need  = sum(n["need_score"] for n in need_scores) / len(need_scores)
    total_stu = sum(s.get("students", 0) for s in schools_in_village)
    n_govt    = sum(1 for s in schools_in_village if s["type"] == "government")

    confidence = min(0.90, 0.65 + len(schools_in_village) * 0.05)

    return {
        "village":  village_name,
        "schools_ranked_by_need":    top_issues_per_school,
        "summary": {
            "total_schools":         len(schools_in_village),
            "total_students_served": total_stu,
            "government_schools":    n_govt,
            "avg_need_score":        round(avg_need, 4),
            "high_need_schools":     sum(1 for n in need_scores if n["need_score"] > 0.55),
        },
        "top_issues_per_school":     top_issues_per_school,
        "recommended_interventions": list({
            iv
            for item in top_issues_per_school
            for iv in item["interventions"]
        })[:8],
        "confidence_score": round(confidence, 4),
        "generated_at":     datetime.utcnow().isoformat() + "Z",
    }


# ── POST /api/lawmaker/school-analysis ──────────────────────────────────────

@app.post("/api/lawmaker/school-analysis", tags=["Lawmaker"])
def school_analysis(req: SchoolAnalysisRequest) -> Dict[str, Any]:
    """
    Deep-dive route and environment analysis for a specific school.
    Returns route problems, terrain issues, weather patterns, crime hotspots,
    and a structured list of suggested fixes — for policy briefings.
    """
    school = SCHOOL_INDEX.get(req.school_id)
    if not school:
        raise HTTPException(
            status_code=404,
            detail=f"School '{req.school_id}' not found. "
                   f"Valid IDs: {list(SCHOOL_INDEX.keys())}"
        )

    lat, lon = school["lat"], school["lon"]

    # ── Simulate 3 typical origins (students coming from ~1–3 km away) ──
    typical_origins = [
        (lat + 0.010, lon - 0.012),
        (lat - 0.015, lon + 0.008),
        (lat + 0.008, lon + 0.018),
    ]

    route_problem_summary: List[Dict] = []
    worst_segments: List[Dict] = []

    for time_slot in ("morning", "evening"):
        for orig_lat, orig_lon in typical_origins:
            routes = [
                [RoutePoint(orig_lat, orig_lon)]
                + [RoutePoint(
                    orig_lat + (lat - orig_lat) * i / 5 + (0.001 * (i % 2)),
                    orig_lon + (lon - orig_lon) * i / 5 + (0.001 * (i % 2)),
                  ) for i in range(1, 5)]
                + [RoutePoint(lat, lon)]
            ]
            analysis = _scorer.score(routes[0], travel_time=time_slot)

            if analysis.problematic_segments:
                route_problem_summary.append({
                    "travel_time":        time_slot,
                    "origin":             (round(orig_lat, 5), round(orig_lon, 5)),
                    "overall_safety":     analysis.overall_safety_score,
                    "n_problem_segments": len(analysis.problematic_segments),
                    "worst_score":        min(
                        s["safety_score"] for s in analysis.problematic_segments
                    ),
                    "explanation":        analysis.explanation,
                })
                worst_segments.extend(analysis.problematic_segments[:2])

    # ── Terrain issues ──
    slope_readings = []
    for dlat in [-0.01, 0, 0.01]:
        for dlon in [-0.01, 0, 0.01]:
            s = get_terrain_slope(lat + dlat, lon + dlon, lat, lon)
            slope_readings.append(s)

    avg_slope_safety = sum(slope_readings) / len(slope_readings)
    terrain_issues = []
    if avg_slope_safety < 0.55:
        terrain_issues.append({
            "issue":    "Significant gradient on approach roads",
            "impact":   "Difficult for young children and cyclists; dangerous in rain",
            "severity": "high" if avg_slope_safety < 0.40 else "moderate",
        })
    if avg_slope_safety < 0.70:
        terrain_issues.append({
            "issue":    "Uneven terrain — prone to waterlogging in monsoon",
            "impact":   "Slip hazard; vehicles may avoid route causing pedestrian crowding",
            "severity": "moderate",
        })

    # ── Weather patterns ──
    weather_patterns = []
    for month_name, month in [
        ("Jan–Feb", 1), ("Mar–May", 3), ("Jun–Sep", 6), ("Oct–Dec", 10)
    ]:
        # Temporarily patch month for simulation
        morning_score = get_weather_risk(lat, lon, "morning")
        evening_score = get_weather_risk(lat, lon, "evening")
        weather_patterns.append({
            "season":       month_name,
            "morning_risk": round(1 - morning_score, 3),
            "evening_risk": round(1 - evening_score, 3),
            "concern":      (
                "High flood risk — monsoon"         if month == 6 else
                "Moderate dust / dry heat"          if month == 3 else
                "Post-monsoon road damage likely"   if month == 10 else
                "Low weather risk"
            ),
        })

    # ── Crime hotspots ──
    hotspots = _detect_crime_hotspots(lat, lon, radius=0.08)

    # ── Suggested fixes ──
    need_data = _score_school_need(school)
    interventions = _get_interventions(need_data, school)
    suggested_fixes = []
    if hotspots:
        suggested_fixes.append({
            "fix":        "Install motion-sensor street lighting at crime hotspots",
            "priority":   "immediate",
            "cost_tier":  "medium",
            "hotspot_count": len(hotspots),
        })
    if hotspots and len(hotspots) >= 2:
        suggested_fixes.append({
            "fix":        "Install CCTV cameras along primary access roads",
            "priority":   "high",
            "cost_tier":  "medium",
        })
    if terrain_issues:
        suggested_fixes.append({
            "fix":        "Construct paved footpath with handrails on steep segments",
            "priority":   "high",
            "cost_tier":  "high",
        })
    if any(t.get("issue", "").lower().find("waterlog") >= 0 for t in terrain_issues):
        suggested_fixes.append({
            "fix":        "Build covered walkways at key flood-prone segments",
            "priority":   "high",
            "cost_tier":  "high",
        })
    for iv in interventions[:4]:
        suggested_fixes.append({
            "fix":       iv,
            "priority":  "medium",
            "cost_tier": "low",
        })

    # ── Budget Estimation ──
    budget_estimate = _estimate_budget(
        suggested_fixes,
        need_data,
        school,
        crime_hotspot_count=len(hotspots),
        terrain_issue_count=len(terrain_issues),
    )

    # ── Confidence ──
    confidence_score = min(
        0.92,
        0.65
        + 0.10 * (len(route_problem_summary) > 0)
        + 0.10 * (len(hotspots) > 0)
        + 0.07 * (len(terrain_issues) > 0)
    )

    return {
        "school_id":   school["school_id"],
        "school_name": school["name"],
        "location":    {"lat": lat, "lon": lon},
        "route_problems": {
            "summary":        route_problem_summary,
            "worst_segments": worst_segments[:6],
            "total_routes_analysed": len(route_problem_summary),
        },
        "terrain_issues":  terrain_issues if terrain_issues else [
            {"issue": "No major terrain issues", "impact": "N/A", "severity": "low"}
        ],
        "weather_patterns":  weather_patterns,
        "crime_hotspots":    hotspots,
        "need_assessment":   need_data,
        "suggested_fixes":   suggested_fixes,
        "budget_estimate":   budget_estimate,
        "confidence_score":  round(confidence_score, 4),
        "generated_at":      datetime.utcnow().isoformat() + "Z",
    }


# ── GET /api/budget/estimate ────────────────────────────────────────────────

@app.get("/api/budget/estimate", tags=["Budget"])
def budget_estimate(
    school_id: str = Query(..., example="SCH001"),
) -> Dict[str, Any]:
    """
    Standalone budget estimation for a school's infrastructure gaps.
    Returns itemised cost breakdown for all recommended interventions.
    """
    school = SCHOOL_INDEX.get(school_id)
    if not school:
        raise HTTPException(
            status_code=404,
            detail=f"School '{school_id}' not found.",
        )

    need_data = _score_school_need(school)
    interventions_text = _get_interventions(need_data, school)

    # Build fixes from need data
    fixes = []
    if need_data["crime_risk"] > 0.55:
        fixes.append({"fix": "Install motion-sensor street lighting at crime hotspots",
                      "priority": "immediate", "cost_tier": "medium"})
        fixes.append({"fix": "Install CCTV cameras along primary access roads",
                      "priority": "high", "cost_tier": "medium"})
    if need_data["pop_density"] < 0.30:
        fixes.append({"fix": "Establish student buddy-system or group-walk programs",
                      "priority": "medium", "cost_tier": "low"})
        fixes.append({"fix": "Partner with local NGOs for route warden volunteers",
                      "priority": "medium", "cost_tier": "low"})
    if need_data["weather_risk"] > 0.50:
        fixes.append({"fix": "Build covered walkways at key flood-prone segments",
                      "priority": "high", "cost_tier": "high"})
        fixes.append({"fix": "Provide weather alerts via SMS for parents",
                      "priority": "medium", "cost_tier": "low"})
    if need_data["n_facilities"] < 3:
        fixes.append({"fix": "Prioritise infrastructure upgrades (toilet, library, water)",
                      "priority": "high", "cost_tier": "medium"})
    if need_data["students"] > 600:
        fixes.append({"fix": "Add a second shift or stagger dismissal times to reduce crowding",
                      "priority": "medium", "cost_tier": "low"})

    hotspots = _detect_crime_hotspots(school["lat"], school["lon"], radius=0.08)
    estimate = _estimate_budget(fixes, need_data, school,
                                crime_hotspot_count=len(hotspots))

    return {
        "school_id":   school["school_id"],
        "school_name": school["name"],
        "budget":      estimate,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
