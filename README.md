# SafeRoute Yadagiri

A comprehensive web application designed to analyze and recommend safe routes for women in Yadagiri district, Karnataka, India. This project leverages data on crime rates, school locations, terrain elevation, weather conditions, and road networks to provide safety-scored route recommendations and policy insights for lawmakers.

## Features

### For Village Users
- **Route Analysis**: Input start and end locations to get safety-scored route options
- **Safety Gauge**: Visual indicators of route safety based on multiple risk factors
- **School Recommendations**: Find nearby schools with safety considerations
- **Interactive Map**: Visualize routes, risk heatmaps, and infrastructure gaps

### For Lawmakers
- **Dashboard**: Comprehensive view of safety metrics across the district
- **Intervention Planning**: Recommendations for safety improvements
- **School Deep Dive**: Detailed analysis of school accessibility and safety
- **Report Export**: Generate reports for policy decisions

### Technical Features
- **Real-time Scoring**: Dynamic route scoring using machine learning models
- **Geospatial Analysis**: Boundary detection, route segmentation, and terrain analysis
- **Data Integration**: Processed datasets from census, crime statistics, and educational records
- **RESTful API**: Backend API for data access and analysis

## Architecture

The application consists of three main components:

- **Backend** (`/backend`): Python Flask API with modules for API routes, geospatial analysis, scoring algorithms, and data processing
- **Frontend** (`/frontend`): React application with Vite build system, featuring interactive maps and user dashboards
- **Data Pipeline** (`/data_collection`): Scripts for fetching, processing, and preparing datasets from various sources

For detailed architecture information, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Git

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Usage

### Running the Application
1. Start the backend server:
   ```bash
   cd backend
   python main.py
   ```

2. In a new terminal, start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser to `http://localhost:5173` (or the port shown by Vite)

### Data Preparation
To prepare the datasets, run the data collection scripts:
```bash
cd data_collection
python prepare_all_data.py
```

## API Documentation

The backend provides RESTful APIs for:
- Route analysis and scoring
- School data retrieval
- Lawmaker insights and interventions

See [API_CONTRACTS.md](docs/API_CONTRACTS.md) for detailed API specifications.

## Data Sources

This project uses data from:
- Karnataka crime statistics (2024)
- Census data (2011) for Yadagiri district
- UDISE educational data
- OpenStreetMap road networks
- Terrain elevation data
- Historical weather data

For more information on data sources and processing, see [DATA_SOURCES.md](docs/DATA_SOURCES.md).

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is developed as part of a hackathon and is intended for educational and research purposes.

## Project Structure

```
├── backend/              # Python Flask API
├── frontend/             # React frontend application
├── data/                 # Processed and raw datasets
├── data_collection/      # Data processing scripts
├── docs/                 # Documentation
└── README.md            # This file
```
