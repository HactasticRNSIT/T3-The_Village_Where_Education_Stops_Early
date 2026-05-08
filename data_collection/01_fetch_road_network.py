"""
SafeRoute AI — Dataset 1: Road Network
Downloads all roads, footpaths, and paths within 15km of Yadagiri village
using the OSMnx library (OpenStreetMap data).
Output: /data/processed/road_network.geojson
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
import json
import os

# ── Configuration ──────────────────────────────────────────────────────────────
LAT, LON = 16.7648, 77.1268          # Yadagiri village centre
RADIUS_M  = 15_000                   # 15 km search radius
OUT_DIR   = "data/processed"
OUT_FILE  = os.path.join(OUT_DIR, "road_network.geojson")

os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 60)
print("DATASET 1 — ROAD NETWORK")
print("=" * 60)

# ── Step 1: Download the full street graph from OSM ───────────────────────────
# network_type='all' includes roads, footpaths, tracks, service roads, etc.
print(f"\n[1/5] Downloading OSM road network within {RADIUS_M/1000:.0f} km …")
try:
    G = ox.graph_from_point(
        (LAT, LON),
        dist=RADIUS_M,
        network_type="all",          # all passable ways
        retain_all=True              # keep isolated nodes (dead-ends, etc.)
    )
    print(f"      Graph: {len(G.nodes):,} nodes, {len(G.edges):,} edges")
except Exception as e:
    print(f"\n  ⚠  OSM/Overpass API unreachable: {e}")
    print("     This is normal in sandboxed/CI environments.")
    print("     On your local machine, run:  python 01_road_network.py")
    print("     Skipping road network download — creating empty placeholder.")
    import json, pathlib
    placeholder = {"type": "FeatureCollection", "features": [],
                   "_note": "Placeholder — run script with internet access to populate"}
    pathlib.Path(OUT_FILE).write_text(json.dumps(placeholder, indent=2))
    print(f"  Placeholder saved → {OUT_FILE}")
    exit(0)

# ── Step 2: Convert edges (roads) to a GeoDataFrame ──────────────────────────
print("[2/5] Converting graph edges to GeoDataFrame …")
edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

# ── Step 3: Keep only the columns we care about ───────────────────────────────
print("[3/5] Selecting and cleaning relevant columns …")
KEEP = ["geometry", "name", "highway", "surface", "lit", "maxspeed",
        "lanes", "width", "access", "oneway", "length"]

# Some columns may be absent in sparse OSM data — add them as NaN if missing
for col in KEEP:
    if col not in edges.columns:
        edges[col] = None

edges = edges[KEEP].copy()

# ── Step 4: Handle list-valued cells (OSM sometimes returns lists) ─────────────
def flatten(val):
    """If OSM returned a list, take the first element."""
    if isinstance(val, list):
        return val[0]
    return val

for col in ["name", "highway", "surface", "lit", "maxspeed"]:
    edges[col] = edges[col].apply(flatten)

# ── Step 5: Report missing values ─────────────────────────────────────────────
print("[4/5] Missing value summary:")
missing = edges.isnull().sum()
total   = len(edges)
for col, n in missing.items():
    if n > 0:
        pct = n / total * 100
        print(f"      {col:<12} {n:>6,} / {total:,}  ({pct:.1f}% missing)")

# Fill critical missings with sensible defaults / flags
edges["surface"]  = edges["surface"].fillna("unknown")
edges["lit"]      = edges["lit"].fillna("unknown")
edges["name"]     = edges["name"].fillna("unnamed")

# ── Step 6: Save as GeoJSON ───────────────────────────────────────────────────
print(f"[5/5] Saving {len(edges):,} road segments → {OUT_FILE}")
edges = edges.to_crs("EPSG:4326")   # ensure WGS-84
edges.to_file(OUT_FILE, driver="GeoJSON")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n── SUMMARY ──────────────────────────────────────────────────")
print(f"  Total road/path segments : {len(edges):,}")
print(f"  Road types (highway)     : {edges['highway'].value_counts().head(6).to_dict()}")
print(f"  Lit status known         : {(edges['lit'] != 'unknown').sum():,} / {len(edges):,}")
print(f"  Surface known            : {(edges['surface'] != 'unknown').sum():,} / {len(edges):,}")
print(f"  Output file              : {OUT_FILE}")
print("─" * 60)
