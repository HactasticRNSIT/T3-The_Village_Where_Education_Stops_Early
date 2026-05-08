"""
SafeRoute AI — Dataset 3: Weather History
Fetches hourly rainfall (precipitation) and visibility data for the past 30 days
from the Open-Meteo API (free, no API key required).
Computes a weather_risk_score (0–1) per hour based on rain + visibility.
Output: /data/processed/weather_history.csv
"""

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────
LAT, LON  = 16.7648, 77.1268
DAYS_BACK = 30
API_URL   = "https://archive-api.open-meteo.com/v1/archive"
OUT_DIR   = "data/processed"
OUT_FILE  = os.path.join(OUT_DIR, "weather_history.csv")

os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 60)
print("DATASET 3 — WEATHER HISTORY (Open-Meteo)")
print("=" * 60)

# ── Step 1: Compute date window ────────────────────────────────────────────────
end_date   = datetime.utcnow().date() - timedelta(days=2)  # API lags ~2 days
start_date = end_date - timedelta(days=DAYS_BACK - 1)
print(f"\n[1/5] Date window: {start_date} → {end_date}  ({DAYS_BACK} days)")

# ── Step 2: Call the Open-Meteo archive API ────────────────────────────────────
print("[2/5] Fetching hourly weather data …")
params = {
    "latitude":        LAT,
    "longitude":       LON,
    "start_date":      str(start_date),
    "end_date":        str(end_date),
    "hourly":          [
        "precipitation",          # mm — rainfall intensity
        "visibility",             # m  — visibility distance
        "rain",                   # mm — rain component
        "cloudcover",             # %  — cloud cover
        "windspeed_10m",          # km/h
        "temperature_2m",         # °C
    ],
    "timezone":        "Asia/Kolkata",
    "windspeed_unit":  "kmh",
}

try:
    resp = requests.get(API_URL, params=params, timeout=60)
    resp.raise_for_status()
    raw = resp.json()
    api_ok = True
    print(f"      API call successful")
except Exception as e:
    print(f"      ⚠  API failed: {e}  — generating synthetic fallback data")
    api_ok = False

# ── Step 3: Parse API response or generate fallback ───────────────────────────
print("[3/5] Parsing data …")

if api_ok:
    hourly = raw["hourly"]
    df = pd.DataFrame({
        "datetime":       pd.to_datetime(hourly["time"]),
        "precipitation":  hourly.get("precipitation",   [None]*len(hourly["time"])),
        "visibility_m":   hourly.get("visibility",      [None]*len(hourly["time"])),
        "rain_mm":        hourly.get("rain",            [None]*len(hourly["time"])),
        "cloudcover_pct": hourly.get("cloudcover",      [None]*len(hourly["time"])),
        "windspeed_kmh":  hourly.get("windspeed_10m",   [None]*len(hourly["time"])),
        "temperature_c":  hourly.get("temperature_2m",  [None]*len(hourly["time"])),
    })
else:
    # Synthetic fallback: recreate realistic Yadagiri monsoon-edge weather
    hours = pd.date_range(
        start=pd.Timestamp(start_date), periods=DAYS_BACK * 24, freq="h",
        tz="Asia/Kolkata"
    )
    rng = np.random.default_rng(42)
    precip = np.clip(rng.exponential(0.8, len(hours)), 0, 40)   # mm, skewed
    df = pd.DataFrame({
        "datetime":       hours,
        "precipitation":  precip.round(2),
        "visibility_m":   np.clip(10000 - precip * 150 + rng.normal(0, 500, len(hours)), 500, 10000).round(0),
        "rain_mm":        precip.round(2),
        "cloudcover_pct": np.clip(precip * 5 + rng.uniform(20, 60, len(hours)), 0, 100).round(0),
        "windspeed_kmh":  np.clip(rng.normal(12, 5, len(hours)), 0, 50).round(1),
        "temperature_c":  (28 + 4 * np.sin(np.linspace(0, 6*np.pi, len(hours))) + rng.normal(0, 1, len(hours))).round(1),
    })

# ── Step 4: Handle missing values ─────────────────────────────────────────────
print("[4/5] Handling missing values …")
missing_before = df.isnull().sum()
for col in ["precipitation", "rain_mm"]:
    df[col] = df[col].fillna(0.0)       # no data = no rain
df["visibility_m"]   = df["visibility_m"].fillna(10000)   # assume clear
df["cloudcover_pct"] = df["cloudcover_pct"].fillna(df["cloudcover_pct"].median())
df["windspeed_kmh"]  = df["windspeed_kmh"].fillna(df["windspeed_kmh"].median())
df["temperature_c"]  = df["temperature_c"].fillna(df["temperature_c"].median())

# ── Step 5: Compute weather_risk_score (0–1) ──────────────────────────────────
# Risk formula:
#   precipitation_risk = min(precipitation / 20, 1)    [20mm/hr = max risk]
#   visibility_risk    = 1 - min(visibility / 5000, 1)  [<5km = increasing risk]
#   Combined:  0.6 * precip_risk + 0.4 * vis_risk

df["precip_risk"] = (df["precipitation"] / 20).clip(0, 1)
df["vis_risk"]    = (1 - (df["visibility_m"] / 5000).clip(0, 1))
df["weather_risk_score"] = (
    0.6 * df["precip_risk"] + 0.4 * df["vis_risk"]
).round(4)

# ── Step 6: Save ──────────────────────────────────────────────────────────────
out_cols = ["datetime", "precipitation", "rain_mm", "visibility_m",
            "cloudcover_pct", "windspeed_kmh", "temperature_c",
            "weather_risk_score"]
df[out_cols].to_csv(OUT_FILE, index=False)
print(f"      Saved {len(df):,} rows → {OUT_FILE}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n── SUMMARY ──────────────────────────────────────────────────")
print(f"  Rows (hourly records)    : {len(df):,}")
print(f"  Date range               : {df.datetime.min()} → {df.datetime.max()}")
print(f"  Avg precipitation        : {df.precipitation.mean():.2f} mm/hr")
print(f"  Max precipitation        : {df.precipitation.max():.1f} mm/hr")
print(f"  Mean visibility          : {df.visibility_m.mean():,.0f} m")
print(f"  Mean risk score          : {df.weather_risk_score.mean():.3f}")
print(f"  High-risk hours (>0.5)   : {(df.weather_risk_score > 0.5).sum():,}")
print(f"  Data source              : {'Open-Meteo API (live)' if api_ok else 'Synthetic fallback'}")
missing_after = df[out_cols].isnull().sum()
if missing_after.any():
    print(f"  Remaining nulls          : {missing_after[missing_after > 0].to_dict()}")
else:
    print("  Remaining nulls          : none")
print("─" * 60)
