"""
SafeRoute AI — prepare_all_data.py
Master pipeline: runs all 6 data preparation scripts in sequence,
then generates the data quality report.

Usage:
    python prepare_all_data.py [--skip-roads]  # skip OSM download in CI/testing

The --skip-roads flag bypasses the heavy OSMnx download (script 1) which
can take 2-5 minutes depending on network speed.
"""

import sys
import time
import subprocess
import os
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
SCRIPTS = [
    ("01_road_network.py", "Road Network (OSMnx — may take 2-5 min)"),
    ("02_terrain.py",      "Terrain Elevation (Open-Elevation API)"),
    ("03_weather.py",      "Weather History (Open-Meteo API)"),
    ("04_schools.py",      "Schools (UDISE+ / synthetic)"),
    ("05_population.py",   "Population (Census 2011)"),
    ("06_crime.py",        "Crime Rates (NCRB 2022)"),
    ("07_quality_report.py", "Data Quality Report"),
]

SKIP_ROADS = "--skip-roads" in sys.argv

# ── Helper ─────────────────────────────────────────────────────────────────────
def run_script(script_path, label):
    print(f"\n{'='*65}")
    print(f"  RUNNING: {label}")
    print(f"  Script : {script_path}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*65}")

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=False,   # stream output live
        text=True,
    )
    elapsed = time.time() - t0

    status = "✅ OK" if result.returncode == 0 else f"❌ FAILED (code {result.returncode})"
    print(f"\n  {status}  —  {elapsed:.1f}s")
    return result.returncode, elapsed

# ── Main ───────────────────────────────────────────────────────────────────────
print("\n" + "█"*65)
print("  SafeRoute AI — Data Preparation Pipeline")
print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("█"*65)

results = []
total_t0 = time.time()

for script_file, label in SCRIPTS:
    # Optionally skip the road network download
    if script_file == "01_road_network.py" and SKIP_ROADS:
        print(f"\n  ⏭  SKIPPED: {label}  (--skip-roads flag set)")
        results.append((script_file, label, "SKIPPED", 0))
        continue

    code, elapsed = run_script(script_file, label)
    status = "OK" if code == 0 else "FAILED"
    results.append((script_file, label, status, elapsed))

# ── Final summary ──────────────────────────────────────────────────────────────
total_elapsed = time.time() - total_t0

print("\n\n" + "═"*65)
print("  PIPELINE COMPLETE — Summary")
print("═"*65)
print(f"  {'Script':<30} {'Status':<10} {'Time':>8}")
print(f"  {'─'*28} {'─'*8} {'─'*8}")
for script_file, label, status, elapsed in results:
    icon = "✅" if status == "OK" else ("⏭ " if status == "SKIPPED" else "❌")
    name = label[:28]
    print(f"  {icon} {name:<28} {status:<10} {elapsed:>6.1f}s")

failed = [r for r in results if r[2] == "FAILED"]
print(f"\n  Total time: {total_elapsed:.1f}s")
print(f"  Passed   : {sum(1 for r in results if r[2]=='OK')}")
print(f"  Skipped  : {sum(1 for r in results if r[2]=='SKIPPED')}")
print(f"  Failed   : {len(failed)}")

if failed:
    print("\n  ⚠  Some scripts failed. Check output above for details.")
    sys.exit(1)
else:
    print("\n  All scripts completed successfully.")
    print("  Check data/processed/ for output files.")
    print("  See data/processed/data_quality_report.md for confidence levels.")

print("═"*65)
