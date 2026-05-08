"""
route_scorer.py — SafeRoute AI Scoring Engine
===============================================
Deterministic, simulation-based safety scoring for student commute routes
in Yadagiri district, Karnataka.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────

def _stable_hash(*args) -> float:
    """Deterministic hash → float in [0, 1] for reproducible simulations."""
    h = hashlib.md5(str(args).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────
# Environment risk simulators
# ─────────────────────────────────────────────

def get_crime_risk(lat: float, lon: float) -> float:
    """Simulated crime risk score [0, 1] for a location."""
    return _stable_hash("crime", round(lat, 3), round(lon, 3))


def get_population_density(lat: float, lon: float) -> float:
    """Simulated population density score [0, 1]."""
    return _stable_hash("pop", round(lat, 3), round(lon, 3))


def get_terrain_slope(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Simulated terrain slope safety [0, 1] — higher = safer/flatter."""
    return 0.3 + 0.7 * _stable_hash(
        "slope", round(lat1, 3), round(lon1, 3), round(lat2, 3), round(lon2, 3),
    )


def get_weather_risk(lat: float, lon: float, travel_time: str = "morning") -> float:
    """Simulated weather safety score [0, 1] — higher = better weather."""
    base = _stable_hash("weather", round(lat, 3), round(lon, 3))
    time_factor = {"morning": 0.05, "afternoon": -0.05, "evening": -0.10}.get(
        travel_time, 0,
    )
    return max(0.0, min(1.0, base + time_factor))


# ─────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────

@dataclass
class RoutePoint:
    lat: float
    lon: float


@dataclass
class SegmentScore:
    start_point: RoutePoint
    end_point: RoutePoint
    distance_km: float
    safety_score: float
    road_quality: float
    terrain_score: float
    crime_score: float
    weather_score: float
    population_score: float
    lighting_score: float


@dataclass
class RouteAnalysis:
    route_id: str
    overall_safety_score: float
    total_distance_km: float
    travel_time_context: str
    explanation: str
    confidence_score: float
    women_safety_warning: Optional[str]
    problematic_segments: List[Dict[str, Any]]
    shap_contributions: Dict[str, float]
    segment_scores: List[SegmentScore]


# ─────────────────────────────────────────────
# Scorer
# ─────────────────────────────────────────────

class RouteScorer:
    """Scores a route (list of RoutePoints) for commute safety."""

    def _score_segment(
        self, start: RoutePoint, end: RoutePoint, travel_time: str,
    ) -> SegmentScore:
        dist = haversine_distance(start.lat, start.lon, end.lat, end.lon)
        mid_lat = (start.lat + end.lat) / 2
        mid_lon = (start.lon + end.lon) / 2

        road_quality = 0.4 + 0.6 * _stable_hash(
            "road", round(mid_lat, 4), round(mid_lon, 4),
        )
        terrain = get_terrain_slope(start.lat, start.lon, end.lat, end.lon)
        crime = 1.0 - get_crime_risk(mid_lat, mid_lon)
        weather = get_weather_risk(mid_lat, mid_lon, travel_time)
        population = get_population_density(mid_lat, mid_lon)
        lighting = 0.3 + 0.7 * _stable_hash(
            "light", round(mid_lat, 4), round(mid_lon, 4),
        )
        if travel_time == "evening":
            lighting *= 0.6

        safety = (
            0.25 * road_quality
            + 0.15 * terrain
            + 0.20 * crime
            + 0.15 * weather
            + 0.10 * population
            + 0.15 * lighting
        )

        return SegmentScore(
            start_point=start,
            end_point=end,
            distance_km=round(dist, 4),
            safety_score=round(safety, 4),
            road_quality=round(road_quality, 4),
            terrain_score=round(terrain, 4),
            crime_score=round(crime, 4),
            weather_score=round(weather, 4),
            population_score=round(population, 4),
            lighting_score=round(lighting, 4),
        )

    def score(
        self, route: List[RoutePoint], travel_time: str = "morning",
    ) -> RouteAnalysis:
        if len(route) < 2:
            raise ValueError("Route must have at least 2 points")

        segments = [
            self._score_segment(route[i], route[i + 1], travel_time)
            for i in range(len(route) - 1)
        ]

        total_dist = sum(s.distance_km for s in segments)
        overall = (
            sum(s.safety_score * s.distance_km for s in segments)
            / max(total_dist, 0.001)
        )

        problematic = [
            {
                "segment_index": i,
                "safety_score": seg.safety_score,
                "start": {"lat": seg.start_point.lat, "lon": seg.start_point.lon},
                "end": {"lat": seg.end_point.lat, "lon": seg.end_point.lon},
                "issues": self._identify_issues(seg),
            }
            for i, seg in enumerate(segments)
            if seg.safety_score < 0.55
        ]

        shap = {
            k: round(sum(getattr(s, attr) for s in segments) / len(segments) - 0.5, 4)
            for k, attr in [
                ("road_quality", "road_quality"),
                ("terrain", "terrain_score"),
                ("crime_safety", "crime_score"),
                ("weather", "weather_score"),
                ("population", "population_score"),
                ("lighting", "lighting_score"),
            ]
        }

        avg_crime = sum(s.crime_score for s in segments) / len(segments)
        avg_light = sum(s.lighting_score for s in segments) / len(segments)
        women_warning = None
        if avg_crime < 0.45 or (travel_time == "evening" and avg_light < 0.40):
            parts = []
            if avg_crime < 0.45:
                parts.append("high crime areas")
            if avg_light < 0.40:
                parts.append("poor lighting")
            women_warning = (
                "\u26a0 This route has elevated safety concerns for women/girls: "
                + " and ".join(parts)
                + ". Consider travelling in groups or using an alternative route."
            )

        explanation = self._generate_explanation(
            overall, segments, problematic, travel_time,
        )

        route_id_hash = f"{_stable_hash(route[0].lat, route[0].lon, route[-1].lat, route[-1].lon):.0f}"
        confidence = min(0.92, 0.60 + len(segments) * 0.05)

        return RouteAnalysis(
            route_id=f"route_{route_id_hash[-8:]}",
            overall_safety_score=round(overall, 4),
            total_distance_km=round(total_dist, 3),
            travel_time_context=travel_time,
            explanation=explanation,
            confidence_score=round(confidence, 4),
            women_safety_warning=women_warning,
            problematic_segments=problematic,
            shap_contributions=shap,
            segment_scores=segments,
        )

    @staticmethod
    def _identify_issues(seg: SegmentScore) -> List[str]:
        checks = [
            (seg.road_quality < 0.50, "Poor road surface quality"),
            (seg.terrain_score < 0.50, "Steep or uneven terrain"),
            (seg.crime_score < 0.45, "High crime area"),
            (seg.weather_score < 0.45, "Weather-exposed segment"),
            (seg.lighting_score < 0.40, "Inadequate street lighting"),
            (seg.population_score < 0.30, "Isolated area with low population"),
        ]
        issues = [msg for cond, msg in checks if cond]
        return issues or ["General safety concern"]

    @staticmethod
    def _generate_explanation(
        overall: float,
        segments: List[SegmentScore],
        problematic: List[dict],
        travel_time: str,
    ) -> str:
        if overall >= 0.75:
            grade, summary = "SAFE", "This route is generally safe for student commuting."
        elif overall >= 0.55:
            grade, summary = "MODERATE", "This route has moderate safety — some segments need caution."
        else:
            grade, summary = "RISKY", "This route has significant safety concerns."

        parts = [f"[{grade}] {summary}"]
        if problematic:
            parts.append(f"{len(problematic)} of {len(segments)} segments flagged.")
            top_issues: set[str] = set()
            for p in problematic[:3]:
                top_issues.update(p.get("issues", []))
            if top_issues:
                parts.append("Key issues: " + "; ".join(list(top_issues)[:3]) + ".")
        parts.append(f"Analysis context: {travel_time} commute.")
        return " ".join(parts)


# ─────────────────────────────────────────────
# Batch scoring
# ─────────────────────────────────────────────

def score_multiple_routes(
    routes: List[List[RoutePoint]], travel_time: str = "morning",
) -> List[RouteAnalysis]:
    """Score multiple candidate routes and return sorted (best first)."""
    scorer = RouteScorer()
    analyses = [scorer.score(route, travel_time) for route in routes]
    analyses.sort(key=lambda a: -a.overall_safety_score)
    return analyses
