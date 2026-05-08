"""
SafeRoute AI — Dataset 2: Terrain Elevation
Samples elevation every 500 m along major roads using the Open-Elevation API
(https://api.open-elevation.com — free, no key required).
Falls back to a synthetic DEM from SRTM-style formula if API is unreachable.
Output: /data/processed/terrain_elevation.csv
  Columns: lat, lon, elevation_m, slope_category
"""

import os
import math
import time
import requests
import json
import numpy as np
import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────────
LAT, LON   = 16.7648, 77.1268
STEP_M     = 500          # sample every 500 m
GRID_RANGE = 15_000       # 15 km radius  →  30 km × 30 km grid
API_URL    = "https://api.open-elevation.com/api/v1/lookup"
BATCH_SIZE = 100          # open-elevation handles up to ~100 points per request
OUT_DIR    = "data/processed"
OUT_FILE   = os.path.join(OUT_DIR, "terrain_elevation.csv")

os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 60)
print("DATASET 2 — TERRAIN ELEVATION")
print("=" * 60)

# ── Step 1: Build a regular grid of sample points ─────────────────────────────
# Convert STEP_M to degrees (approx): 1° lat ≈ 111 km, 1° lon ≈ 111*cos(lat) km
step_lat = STEP_M / 111_000
step_lon = STEP_M / (111_000 * math.cos(math.radians(LAT)))

n_half   = int(GRID_RANGE / STEP_M)   # steps each side of centre
lat_vals = [LAT + i * step_lat for i in range(-n_half, n_half + 1)]
lon_vals = [LON + i * step_lon for i in range(-n_half, n_half + 1)]

points = [{"latitude": round(la, 6), "longitude": round(lo, 6)}
          for la in lat_vals for lo in lon_vals]

print(f"[1/4] Generated {len(points):,} sample points on a {STEP_M}m grid")

# ── Step 2: Query elevation (batched) ─────────────────────────────────────────
def fetch_elevations(pts):
    """Call Open-Elevation API in batches; return list of elevation_m values."""
    elevations = []
    for i in range(0, len(pts), BATCH_SIZE):
        batch = pts[i: i + BATCH_SIZE]
        try:
            resp = requests.post(
                API_URL,
                json={"locations": batch},
                timeout=30,
                headers={"Accept": "application/json",
                         "Content-Type": "application/json"}
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            elevations.extend([r.get("elevation", None) for r in results])
        except Exception as e:
            print(f"      API error (batch {i//BATCH_SIZE}): {e} — using fallback")
            elevations.extend([None] * len(batch))
        time.sleep(0.3)   # be polite to the free API
    return elevations

print("[2/4] Querying Open-Elevation API …")
elevations = fetch_elevations(points)

# ── Step 3: Fallback — synthetic elevation for any None values ────────────────
# Yadagiri sits on the Deccan Plateau at ~400-450 m asl.
# Simple model: base 420 m + small sinusoidal variation to mimic gentle terrain.
def synthetic_elevation(la, lo):
    """Deterministic pseudo-elevation for demo / fallback purposes."""
    base   = 420.0
    relief = 30 * math.sin(math.radians(la * 180)) * math.cos(math.radians(lo * 90))
    noise  = 5  * math.sin(math.radians(la * 360 + lo * 270))
    return round(base + relief + noise, 1)

filled_count = 0
for idx, (pt, el) in enumerate(zip(points, elevations)):
    if el is None:
        elevations[idx] = synthetic_elevation(pt["latitude"], pt["longitude"])
        filled_count += 1

if filled_count:
    print(f"      ⚠  {filled_count:,} points filled with synthetic elevation (API unavailable)")

# ── Step 4: Compute slope and classify ────────────────────────────────────────
# We approximate slope between adjacent grid rows (N-S direction)
print("[3/4] Computing slope categories …")

df = pd.DataFrame({
    "lat":         [p["latitude"]  for p in points],
    "lon":         [p["longitude"] for p in points],
    "elevation_m": elevations
})

# Compute approximate slope (%) using finite differences across the grid
n_cols = len(lon_vals)
elev_arr = np.array(df["elevation_m"].values, dtype=float).reshape(
    len(lat_vals), n_cols
)

# Slope = |Δelevation| / distance × 100%
dy = step_lat * 111_000   # metres per row step
dx = step_lon * 111_000 * math.cos(math.radians(LAT))  # metres per col step

grad_y = np.gradient(elev_arr, dy, axis=0)   # m/m
grad_x = np.gradient(elev_arr, dx, axis=1)
slope_pct = np.sqrt(grad_x**2 + grad_y**2) * 100   # percentage

df["slope_pct"] = slope_pct.flatten().round(2)

def classify_slope(s):
    if s < 3:   return "flat"
    if s < 8:   return "moderate"
    return "steep"

df["slope_category"] = df["slope_pct"].apply(classify_slope)

# ── Step 5: Save ──────────────────────────────────────────────────────────────
print(f"[4/4] Saving {len(df):,} rows → {OUT_FILE}")
df[["lat", "lon", "elevation_m", "slope_pct", "slope_category"]].to_csv(
    OUT_FILE, index=False
)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n── SUMMARY ──────────────────────────────────────────────────")
print(f"  Total sample points      : {len(df):,}")
print(f"  Elevation range          : {df.elevation_m.min():.1f} – {df.elevation_m.max():.1f} m")
print(f"  Mean elevation           : {df.elevation_m.mean():.1f} m")
print(f"  Slope distribution       :")
for cat, cnt in df.slope_category.value_counts().items():
    print(f"      {cat:<10} {cnt:>6,}  ({cnt/len(df)*100:.1f}%)")
print(f"  Synthetic fill count     : {filled_count:,}")
print(f"  Output file              : {OUT_FILE}")
print("─" * 60)
