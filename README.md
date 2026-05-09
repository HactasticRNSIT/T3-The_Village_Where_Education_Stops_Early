<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" />
  <img src="https://img.shields.io/badge/TailwindCSS_4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white" />
</p>

# 🛡️ SafeRoute AI

> **AI-powered student commute safety scoring for Yadagiri, Karnataka**

SafeRoute AI is a full-stack web application that helps students, parents, and policymakers in the Yadagiri district of Karnataka find the **safest routes to school**. It combines **6 safety factors** — road quality, terrain, weather, crime risk, population density, and street lighting — into a single, explainable safety score for every route.

---

## 🌟 Problem Statement

In rural Yadagiri district, thousands of students walk to school every day through roads with poor lighting, flood-prone terrain, and high-crime areas. Families have no data-driven way to choose the safest commute path, and lawmakers lack the granular evidence needed to prioritise infrastructure spending. **SafeRoute AI bridges this gap.**

---

## ✨ Key Features

### 🗺️ Route Safety Analyzer
- Enter any origin location → get **3 candidate routes** to each nearby school, ranked by safety
- **SHAP-style contribution bars** showing which factors drive the score (road quality, crime, weather, etc.)
- **Women/girls safety warnings** for routes through high-crime or poorly-lit areas
- Interactive Leaflet map with color-coded routes (🟢 Safe · 🟡 Moderate · 🔴 Risky)

### 🏫 School Finder
- Search for schools within a configurable radius (GeoJSON boundary query)
- View school type, grades, student count, medium of instruction, and facilities
- **Need Score** indicating how urgently each school requires safety intervention

### 📊 Lawmaker Dashboard
- **Village Report** — aggregate safety stats, schools ranked by need, top issues, and recommended interventions
- **School Deep-Dive** — per-school route problems, terrain issues, seasonal weather patterns, crime hotspots, and suggested fixes
- **💰 Budget Intervention Estimator** — itemised cost breakdown in INR (based on Karnataka RDPR & PMGSY 2024-25 benchmark rates), category charts, and grand total

### 📄 PDF Report Export
- One-click branded PDF download of Village Reports and School Analyses via `html2pdf.js`

### 🌐 Multi-Language Support
- UI available in **English**, **हिन्दी (Hindi)**, and **ಕನ್ನಡ (Kannada)**
- Language switcher in the navbar; dynamic content is also translated

---

## 🏗️ Architecture

```
SafeRoute AI
├── backend/                    # Python FastAPI server (port 8000)
│   ├── main.py                 # App entry point + all endpoints
│   ├── scoring/
│   │   ├── route_scorer.py     # Core safety scoring engine
│   │   ├── explainer.py        # SHAP-style explanations
│   │   ├── interventions.py    # Intervention mapping logic
│   │   └── women_safety.py     # Gender-specific safety warnings
│   ├── geo/
│   │   ├── boundary.py         # GeoJSON boundary queries
│   │   ├── route_finder.py     # Route generation & interpolation
│   │   └── segment_analyzer.py # Per-segment analysis
│   ├── models/
│   │   ├── request_models.py   # Pydantic request schemas
│   │   └── response_models.py  # Pydantic response schemas
│   ├── api/
│   │   ├── routes.py           # /api/routes/* handlers
│   │   ├── schools.py          # /api/schools/* handlers
│   │   └── lawmaker.py         # /api/lawmaker/* handlers
│   └── requirements.txt
│
├── frontend/                   # Vanilla JS + Vite + TailwindCSS 4
│   ├── index.html              # Single-page application
│   ├── app.js                  # Application logic & rendering
│   ├── translations.js         # i18n engine (EN / HI / KN)
│   ├── styles.css              # Design system & component styles
│   ├── vite.config.js          # Vite + Tailwind plugin config
│   └── package.json
│
├── data_collection/            # Data preparation pipeline
│   ├── 01_fetch_road_network.py    # OSMnx road network download
│   ├── 02_fetch_terrain.py         # Open-Elevation API
│   ├── 03_fetch_weather.py         # Open-Meteo historical weather
│   ├── 04_parse_udise.py           # UDISE+ school data parser
│   ├── 05_parse_census.py          # Census 2011 population data
│   ├── 06_parse_crime.py           # NCRB 2022 crime statistics
│   ├── 07_quality_report.py        # Data quality assessment
│   └── prepare_all_data.py         # Master pipeline runner
│
├── data/
│   ├── raw/                    # Original source data
│   └── processed/              # Pipeline outputs (CSV, GeoJSON)
│       ├── schools_yadagiri.csv
│       ├── road_network.geojson
│       ├── terrain_elevation.csv
│       ├── weather_history.csv
│       ├── population.csv
│       ├── crime_rates.csv
│       └── data_quality_report.md
│
└── docs/                       # Extended documentation
    ├── API_CONTRACTS.md
    ├── ARCHITECTURE.md
    ├── DATA_SOURCES.md
    ├── CONTRIBUTING.md
    └── MAPS_LAYER.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Deployment health check + schools loaded count |
| `POST` | `/api/routes/analyze` | Route safety analysis (origin → nearby schools) |
| `GET` | `/api/schools/boundary` | Schools within radius as GeoJSON FeatureCollection |
| `GET` | `/api/lawmaker/village-report` | Village-level needs report for policymakers |
| `POST` | `/api/lawmaker/school-analysis` | Deep-dive school route & environment analysis |

> 📖 Interactive API docs available at **`http://localhost:8000/docs`** (Swagger UI) and **`/redoc`** (ReDoc)

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Git | 2.x |

### 1. Clone the Repository

```bash
git clone https://github.com/HactasticRNSIT/T3-The_Village_Where_Education_Stops_Early.git
cd T3-The_Village_Where_Education_Stops_Early
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install Python dependencies
pip install -r backend/requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the Application

Open **two terminals**:

**Terminal 1 — Backend (FastAPI + Uvicorn):**
```bash
cd backend
python main.py
```
> Backend starts at **http://localhost:8000**

**Terminal 2 — Frontend (Vite dev server):**
```bash
cd frontend
npm run dev
```
> Frontend starts at **http://localhost:5173**

### 5. Open in Browser

Navigate to **http://localhost:5173** — you should see the SafeRoute AI interface with the status indicator showing `Online · 8 schools`.

---

## 📊 Data Pipeline

The data collection pipeline fetches and processes 6 datasets for the Yadagiri district:

```bash
cd data_collection
python prepare_all_data.py            # Run all 7 scripts in sequence
python prepare_all_data.py --skip-roads  # Skip the heavy OSMnx download
```

| # | Script | Source | Output |
|---|--------|--------|--------|
| 1 | `01_fetch_road_network.py` | OpenStreetMap (via OSMnx) | `road_network.geojson` |
| 2 | `02_fetch_terrain.py` | Open-Elevation API | `terrain_elevation.csv` |
| 3 | `03_fetch_weather.py` | Open-Meteo API | `weather_history.csv` |
| 4 | `04_parse_udise.py` | UDISE+ (synthetic) | `schools_yadagiri.csv` |
| 5 | `05_parse_census.py` | Census 2011 | `population.csv` |
| 6 | `06_parse_crime.py` | NCRB 2022 | `crime_rates.csv` |
| 7 | `07_quality_report.py` | All above | `data_quality_report.md` |

All outputs are written to `data/processed/`.

---

## ⚙️ Safety Scoring Model

The route scorer evaluates each **segment** of a route using 6 weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Road Quality | 25% | Surface condition of the road segment |
| Crime Safety | 20% | Inverse of crime risk in the area |
| Terrain | 15% | Slope steepness — flatter is safer |
| Weather | 15% | Weather exposure risk (varies by time of day) |
| Street Lighting | 15% | Availability of lighting (reduced weight in evening) |
| Population Density | 10% | Presence of bystanders along the route |

The **overall route score** is a distance-weighted average of all segment scores. Segments scoring below **0.55** are flagged as problematic with specific issue descriptions.

### Women/Girls Safety Warnings

Routes through areas with crime index > 0.55 or evening lighting < 0.40 trigger dedicated safety warnings recommending group travel or alternative routes.

---

## 💰 Budget Intervention Estimator

The budget engine maps suggested infrastructure fixes to itemised costs based on **Karnataka RDPR & PMGSY 2024-25 benchmark rates**:

| Item | Unit Cost (₹) | Unit |
|------|---------------|------|
| Solar LED Street Lighting | ₹18,000 | per pole |
| CCTV Surveillance Camera | ₹35,000 | per camera |
| Road Paving (CC/Bitumen) | ₹25,00,000 | per km |
| Covered Bus Stop Shelter | ₹1,20,000 | per shelter |
| Covered Walkway (Flood-Prone) | ₹3,50,000 | per 100m |
| Toilet Block (4 units, SBM spec) | ₹2,80,000 | per block |
| Community Police Escort Program | ₹1,80,000 | per year |
| SMS Weather Alert System | ₹45,000 | per setup |

> Estimates may vary ±20% based on site conditions and contractor rates.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Frontend** | Vanilla JavaScript (ES Modules), HTML5 |
| **Build Tool** | Vite 8 |
| **Styling** | TailwindCSS 4, Custom CSS design system |
| **Maps** | Leaflet.js + OpenStreetMap tiles |
| **PDF Export** | html2pdf.js |
| **i18n** | Custom translations engine (EN / HI / KN) |
| **Data Pipeline** | Python scripts (OSMnx, requests, csv) |

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is developed as part of a hackathon and is intended for educational and research purposes.

---

## 👥 Team

**Team T3** — HactasticRNSIT  
*The Village Where Education Stops Early*

---

<p align="center">
  <sub>Built with ❤️ for safer student commutes in Yadagiri, Karnataka</sub>
</p>
