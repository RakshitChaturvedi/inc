# OceanEmbed Operations Console & API

Frontend operations console and FastAPI backend for the OceanEmbed ensemble daily ocean subsurface prediction system.

---

## Architecture Overview

- **Frontend (`src/`)**: React + Vite + TypeScript console with MapLibre GL / deck.gl visualization. Proxies `/api` requests to `http://127.0.0.1:8000`.
- **Backend (`backend/`)**: FastAPI server exposing clean REST endpoints under `/api/v1/ocean/*`.
- **Data Layer (`backend/api/dataset.py`)**: Reads multi-dimensional ocean data lazily from NetCDF and evaluation metrics from JSON.

---

## Multi-System Deployment Note

> **Note on Datasets**: The production datasets and model reside on the target/production system. This codebase was integrated and validated so that placing the production artifacts on the target system immediately projects real data onto the UI without modifying any code.

### Required Files on the Target System:
1. `backend/data/business/dashboard_ready.nc`
   - Contains 4D variables (`temperature_mean`, `temperature_std`, `salinity_mean`, `salinity_std`) and 3D variables (`tchp`, `d26`, `mld`, `thermocline_depth`).
   - Can also be set via environment variable: `DASHBOARD_DATASET_PATH=/path/to/dashboard_ready.nc`
2. `backend/data/evaluation/evaluation_report.json`
   - Contains model evaluation metrics, global RMSE, and run timestamp.
   - Can also be set via environment variable: `EVALUATION_REPORT_PATH=/path/to/evaluation_report.json`

---

## How to Run

### 1. Backend (FastAPI)
```bash
cd backend
# Create/activate virtualenv and install dependencies
pip install -r requirements.txt
# Run the API server
uvicorn main:app --host 0.0.0.0 --port 8000
```
API docs available at: `http://localhost:8000/docs`

### 2. Frontend (Vite)
```bash
# In the repository root
npm install
npm run dev
```
Console available at: `http://localhost:5173/`

---

## Verified Endpoints (`/api/v1/ocean/*`)

- `GET /api/v1/ocean/health` — Run status, data window, and `lastUpdated` from evaluation report.
- `GET /api/v1/ocean/argo` — Active ARGO floats with coordinates and IDs.
- `GET /api/v1/ocean/field` — 2D slice of reconstructed ocean variable (`temperature`, `salinity`, `uncertainty`, `tchp`, `d26`, `mld`) for map rendering.
- `GET /api/v1/ocean/profile` — Full vertical depth profile (0–1000m) for any clicked ocean coordinate.
- `GET /api/v1/ocean/tchp` — Tropical Cyclone Heat Potential and D26 isotherm depth.
- `GET /api/v1/ocean/d26` — Depth of the 26°C isotherm.
- `GET /api/v1/ocean/mld` — Mixed-layer depth.
- `GET /api/v1/ocean/uncertainty` — Model standard deviation at specified depth.
- `GET /api/v1/ocean/evaluation` — Model evaluation report and physics validation metrics.
