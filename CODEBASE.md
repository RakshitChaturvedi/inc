# OceanEmbed Codebase Reference

This document describes the **OceanEmbed Operations Console & API** repository: a daily North Indian Ocean subsurface reconstruction system. The product reconstructs temperature and salinity on a **0.25° × 0.25°** grid from **5°N–30°N, 45°E–105°E**, at **15 depths from 0–1000 m**, using a five-member **CBAM-CNN (U-Net)** ensemble.

The repository has two runtime surfaces:

| Layer | Location | Stack | Role |
| --- | --- | --- | --- |
| **Frontend** | `src/` (repo root) | React 18, Vite 6, TypeScript, MapLibre GL, deck.gl | Operations console: map, depth rail, click-to-profile panel |
| **Backend** | `backend/` | FastAPI, xarray/NetCDF, PyTorch | Offline science pipeline **and** REST API that serves dashboard NetCDF |

They are loosely coupled. The FastAPI process never trains the model at request time. It reads **precomputed** NetCDF/JSON artifacts. The frontend talks only to HTTP endpoints under `/api/v1/ocean/*`.

---

## 1. How the pieces fit together

### 1.1 End-to-end data flow (offline science → live UI)

```
Satellite / altimetry / wind / currents  (PO.DAAC + Copernicus)
        │
        ▼
backend/ocean/acquisition/*     →  backend/data/raw/{sst,sss,ssh,wind,currents}/
        │
        ▼
backend/ocean/preprocessing/*   →  12-channel tensor [1, 12, 101, 241]
        │                            (or full-period [1419, 101, 241, 12] NetCDF)
        ▼
backend/ocean/inference/*        →  ensemble_predictions.nc
                                     ensemble_member_predictions.nc
        │
        ▼
backend/ocean/postprocessing/*   →  backend/data/physics/physics_adjusted.nc
        │
        ├──────────────────────────► backend/ocean/evaluation/*  → evaluation_report.json
        │
        ▼
backend/ocean/business/*         →  backend/data/business/dashboard_ready.nc
        │                            (T/S mean+std + TCHP, D26, MLD, thermocline)
        ▼
FastAPI (backend/main.py)        →  JSON over /api/v1/ocean/*
        │
        ▼
Vite proxy /api → :8000           →  React console (src/App.tsx)
```

**Grid contract used everywhere:** 101 latitudes × 241 longitudes = `(5.00 … 30.00)` × `(45.00 … 105.00)` at 0.25°. Depths: `0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000` m.

**Model input channels (order is a hard contract):** SST, SSS, SSHA, wind_U, wind_V, current_U, current_V, wind_stress_curl, latitude, longitude, sin_day_of_year, cos_day_of_year.

**Model output:** dual heads, 15 depth layers each, for temperature and salinity. Five ensemble members → mean and standard deviation.

### 1.2 Live request path (what happens when a user clicks the map)

1. `App` holds date, field (`temperature` | `salinity` | `uncertainty` | `tchp` | `mld`), depth index, and selected lat/lon.
2. `oceanApi` in `src/api/apiClient.ts` `fetch`es `/api/v1/ocean/...`. Vite proxies `/api` to `http://127.0.0.1:8000`.
3. FastAPI routes open `dashboard_ready.nc` (lazily, cached) and snap the click to the nearest 0.25° cell.
4. JSON is mapped into UI types. If the backend is down, **status / ARGO / field** fall back to `mockOceanApi.ts`. **Profile / TCHP / MLD / uncertainty** return `null` rather than mocked science values (except field/status/argo).

### 1.3 Domain rules shared by both sides

| Rule | Backend | Frontend |
| --- | --- | --- |
| Geographic box | `backend/api/coordinates.py` | `GeospatialService.isInDomain`, `apiClient.isOutOfDomain` |
| 0.25° snap | `get_nearest_model_cell` | `geoService.getNearestModelCell` |
| Land vs ocean | API does not apply a land mask on all routes; land cells often appear as NaN/`null` | `geoService.isLand` using `/land.geojson` (and a crude polygon fallback) |

---

## 2. Repository layout (non-code)

| Path | Purpose |
| --- | --- |
| `README.md` | Short run instructions and endpoint list |
| `package.json` / `package-lock.json` | Frontend dependencies and `dev` / `build` / `preview` scripts |
| `index.html` | Vite HTML shell; mounts `#root` |
| `vite.config.ts` | Dev server `0.0.0.0:5173`, `/api` proxy to backend `:8000` |
| `tsconfig.json` | TypeScript for `src/` |
| `tsconfig.node.json` | TypeScript for `vite.config.ts` |
| `.gitignore` | Ignores `node_modules`, `dist`, venv, `__pycache__` |
| `backend/requirements.txt` | Python deps: FastAPI, uvicorn, numpy, xarray, netcdf4, torch, scipy |
| `backend/config/acquisition.yaml` | Date window, domain, Copernicus/PO.DAAC product IDs |
| `backend/data/business/dashboard_ready.nc` | **Primary API dataset** (production or sample) |
| `backend/data/physics/physics_adjusted.nc` | Physics-adjusted T/S ensemble stats |
| `backend/data/evaluation/evaluation_report.json` | Evaluation (or related) JSON consumed by health/evaluation routes |

There is **no** `Dockerfile`, `docker-compose.yml`, or `.dockerignore` in this repository. See [Section 6](#6-docker-and-deployment).

Artifacts that the code **expects** but that are often **not in git** (they live on the production/training machine):

- `backend/model-registry/oceanembed-v1.0.0/` — `manifest.json`, five `.pt` checkpoints, `depths.json`, `normalization_stats.json`, `ocean_mask_3d.nc`
- `backend/data/raw/**` — downloaded satellite NetCDFs
- `backend/data/inference/input_tensor_normalized.nc`, `ensemble_predictions.nc`, `ensemble_member_predictions.nc`
- `public/land.geojson` — land mask for the map (referenced as `/land.geojson`; not present in this tree)
- Evaluation ground truth: `temperature_targets_masked.nc`, `salinity_targets_masked.nc`

---

## 3. Backend

Two FastAPI entrypoints exist. **The documented process is `backend/main.py`.**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

- `backend/main.py` — CORS for Vite (`localhost:5173` / `127.0.0.1:5173`), mounts `/api/v1/ocean`, plus `GET /health` `{status, service}`.
- `backend/api/main.py` — alternate app that only mounts the ocean router and `GET /`. Not used by the README.

Python imports assume **cwd = `backend/`** (`from api.router import router`, `from ocean.evaluation...`).

### 3.1 API core (`backend/api/`)

#### `dataset.py`

**Purpose:** Single place that opens NetCDF/JSON artifacts.

**Inputs:**

- Env `OCEAN_DATA_DIR` (default `backend/data`)
- Env `DASHBOARD_DATASET_PATH` or `OCEAN_DASHBOARD_PATH` (default `data/business/dashboard_ready.nc`)
- Env `PHYSICS_ADJUSTED_PATH` (default `data/physics/physics_adjusted.nc`)
- Env `EVALUATION_REPORT_PATH` or `OCEAN_EVALUATION_REPORT_PATH` (default `data/evaluation/evaluation_report.json`)

**Outputs / API:**

- Module singleton `dataset: OceanDataset`
- `get_dashboard_dataset()` — LRU-cached `xr.open_dataset`
- Methods: `field_at`, `profile_at`, `value_at`, `nearest_*`, `summary()`, `evaluation_report`

Expected dashboard variables: `temperature_mean`, `temperature_std`, `salinity_mean`, `salinity_std`, `tchp`, `d26`, `mld`, `thermocline_depth` on dims `time, depth, latitude, longitude` (scalars omit `depth`).

#### `dependencies.py`

**Input:** global `dataset`.  
**Output:** FastAPI `Depends` generators. Raises `DatasetUnavailableError` (HTTP 503) if files are missing. `get_physics_dataset` is defined but unused by current routes.

#### `schemas.py`

Pydantic models for JSON responses: `RunStatusResponse`, `FieldResponse`/`FieldPoint`, `ProfileResponse`, `TchpResponse`, `D26Response`, `MldResponse`, `ThermoclineResponse`, `UncertaintyResponse`, `SamplingRecommendation`, `ArgoFloatResponse`.

#### `coordinates.py`

**Input:** lat, lon.  
**Output:** `ModelCoordinate` snapped to 0.25°. Raises `ValueError` outside 5–30°N, 45–105°E.

#### `dates.py`

Helpers: ISO week (`2026-W35`), `normalize_date`, `get_available_dates` from xarray times.

#### `errors.py`

Two overlapping exception families (`OceanAPIError` with status codes, and a second `OceanEmbedAPIError` set). Duplicate class names (`InvalidCoordinateError`, `InvalidDateError`) mean the later `OceanAPIError` subclasses win. Handlers `ocean_api_exception_handler` / `generic_exception_handler` exist but **are not registered** on `backend/main.py`.

#### `router.py`

**Input:** route modules.  
**Output:** `APIRouter(prefix="/api/v1/ocean")` including health, metadata, evaluation, argo, field, profile, tchp, d26, mld, thermocline, uncertainty, sampling.

### 3.2 HTTP routes (`backend/api/routes/`)

All URLs below are relative to `http://localhost:8000`.

| File | Method / path | Query inputs | Output |
| --- | --- | --- | --- |
| `health.py` | `GET /api/v1/ocean/health` | none | `analysisWeek`, `modelVersion`, `gateStatus` (`published` if dashboard exists else `blocked`), `sourceWindow` from dataset time range, `lastUpdated` from evaluation JSON `timestamp` |
| `metadata.py` | `GET /api/v1/ocean/metadata` | none | dims, variables, time span, depths, lat/lon ranges, `grid_resolution: 0.25` |
| `evaluation.py` | `GET /api/v1/ocean/evaluation` | none | raw evaluation JSON, or 404 |
| `argo.py` | `GET /api/v1/ocean/argo` | `date`, `week` (ignored) | **hardcoded** 8 floats (`WMO 2900`–`2907`) |
| `field.py` | `GET /api/v1/ocean/field` | `variable` (required), `date`, `depth`, `stride≥1` | Flattened lat/lon points. Maps `temperature→temperature_mean`, `salinity→salinity_mean`, `uncertainty→temperature_std`, plus `tchp`/`d26`/`mld`. Depth ignored for 2D business fields |
| `profile.py` | `GET /api/v1/ocean/profile` | `date`, `lat`∈[5,30], `lon`∈[45,105] | Full 15-level T/S + uncertainties + TCHP/D26/MLD/thermocline at nearest cell. Falls back to first time if date missing |
| `tchp.py` | `GET /api/v1/ocean/tchp` | `date`, `lat`, `lon` | TCHP value, category (`Too Low` / `Medium (Baseline)` / `High (Good)` / `Too High (Extreme Energy)`), D26 |
| `d26.py` | `GET /api/v1/ocean/d26` | `date`, `lat`, `lon` | D26 + companion TCHP |
| `mld.py` | `GET /api/v1/ocean/mld` | `date`, `lat`, `lon` | Mixed-layer depth (m) |
| `thermocline.py` | `GET /api/v1/ocean/thermocline` | `date`, `lat`, `lon` | `thermocline_depth`; **does not** fall back if date missing |
| `uncertainty.py` | `GET /api/v1/ocean/uncertainty` | `date`, `lat`, `lon`, `depth` | `temperature_std` and `salinity_std` at exact model depth |
| `sampling.py` | `GET /api/v1/ocean/sampling` | `date`, optional `lat`/`lon`, `top_n` 1–100 (default 20) | Ranked cells by 0.5×norm(T_std)+0.5×norm(S_std) at surface; optional 5×5 neighborhood around a click |

`profile.py` attaches its route as `/profile` on a router **without** a prefix, then the parent prefix yields `/api/v1/ocean/profile`. Other files use `prefix="/tchp"` etc. plus `""`.

### 3.3 Acquisition (`backend/ocean/acquisition/`)

**Entry:** `python -m ocean.acquisition.download_all` (from `backend/`).

| File | Role | Inputs | Outputs |
| --- | --- | --- | --- |
| `download_all.py` | Orchestrator | `config/acquisition.yaml` | Creates `output_root`, calls Copernicus then PO.DAAC |
| `common.py` | Date helpers | filenames containing `YYYYMMDD` | Missing date ranges for incremental download |
| `copernicus.py` | CMEMS subset | product `SEALEVEL_GLO_PHY_L4_NRT_008_046`; prefers daily NRT dataset and variables `sla`/`zos`/`sea_level_anomaly` | `data/raw/ssh/ssh_2025_2026.nc`. ARMOR3D is **disabled** in YAML (validation product, not a model input) |
| `podaac.py` | NASA Earthdata via CLI `podaac-data-downloader` | collections in YAML: AVHRR SST, OISSS, CCMP winds, OSCAR currents | `data/raw/{sst,sss,wind,currents}/*.nc` for missing date ranges |

**YAML (`backend/config/acquisition.yaml`):** dates `2025-01-01`–`2026-08-01`, domain 5–30°N / 45–105°E, resolution 0.25, `output_root: data/raw`.

### 3.4 Preprocessing (`backend/ocean/preprocessing/`)

**Entry:** `process_daily_forecast(date_str, raw_data_dir, registry_dir)` in `pipeline.py`.

| File | Role | Inputs | Outputs |
| --- | --- | --- | --- |
| `pipeline.py` | Daily orchestrator | date `YYYY-MM-DD`, raw dirs, model registry | `np.ndarray` shape `[1, 12, 101, 241]` float32 |
| `schema.py` | Coordinate/time schema | any NetCDF | lat/lon named `latitude`/`longitude`, time as datetime64, unique times |
| `harmonize.py` | Variable rename | SST `analysed_sst`→`sst`; SSH `sla`→`ssh`; winds `uwnd`/`vwnd`; currents `u`/`v` | Single-source datasets with OceanEmbed names |
| `temporal.py` | Time alignment | datasets; wind is sub-daily | `daily_mean` for wind; `align_daily` linear interp onto the target day; `derive_wind_speed` |
| `spatial.py` | Geographic crop | lat/lon bounds | Subset dataset; errors if no overlap |
| `regrid.py` | xESMF bilinear regrid | source + target 0.25° grid | Dataset on 101×241; caches weights under `data/processed/phase2/weights` |
| `features.py` | Derived channels | `wind_u`/`wind_v`, coords, time | `wind_stress_curl`, 2D lat/lon fields, sin/cos day-of-year |
| `normalize.py` | Z-score | `registry_dir/oceanembed-v1.0.0/normalization_stats.json` | Normalized variables; temporal sin/cos left raw |
| `tensor.py` | Channel stack + land mask | 12 variables; optional `oceanembed-v1/ocean_mask.nc` | `[1, 12, 101, 241]`; land → 0 |
| `validate.py` | Contract check | tensor | Prints dtype/shape/NaN/z-score sanity; expected shape `(1,12,101,241)` |
| `test_preprocessing.py` | Smoke test | first files in `data/raw/*` | Runs pipeline + `validate_tensor` |

**Note:** Harmonize uses `wind_u`/`current_u` while `normalize.py` mapping keys include `wind_U`/`current_U`. The tensor builder uses lowercase `wind_u`. Full-period inference (`run_inference.py`) reads a **pre-built** `input_tensor_normalized.nc` with channel names SST/SSS/… rather than calling `process_daily_forecast` for all 1419 days.

### 3.5 Inference (`backend/ocean/inference/`)

**Architecture:** dual-head U-Net with optional CBAM.

| File | Role | Inputs | Outputs |
| --- | --- | --- | --- |
| `oceanembed.py` | `OceanEmbedModel` | `[B, 12, 101, 241]` | `(temperature, salinity)` each `[B, 15, 101, 241]` |
| `encoder.py` | 4 stages 12→64→128→256→512, ELU, MaxPool, skip+CBAM | tensor | latent + 4 skip maps |
| `bottleneck.py` | Conv-BN-ELU ×2 + attention | `[B,512,H,W]` | same shape |
| `decoder.py` | 4 upsample/concat stages; 1×1 conv to 15 depths | latent + skips | `[B,15,H,W]` |
| `cbam.py` | Channel + spatial attention | feature maps | reweighted features |
| `model_registry.py` | Reads `manifest.json` | registry root | architecture dict, member checkpoint paths |
| `model_loader.py` | Instantiates 5 models, `load_state_dict` | registry, `torch.device` | list of eval-mode models |
| `ensemble.py` | Forward all members | numpy `[1,12,101,241]` | stacked `[5,15,101,241]` T and S |
| `run_inference.py` | **Batch job** | `data/inference/input_tensor_normalized.nc` shape **`(1419,101,241,12)`**, registry `depths.json` | `ensemble_predictions.nc` (mean/std) and `ensemble_member_predictions.nc` (per member). CUDA if available |
| `validate_input.py` | CLI check of input tensor vs channel list and shape `(1419,101,241,12)` | NetCDF + registry | pass/fail print |
| `validate_models.py` | CLI: 5 members, load weights | `manifest.json` + `.pt` | pass/fail print |
| `test_inference.py` | Random tensor through ensemble | `model-registry/` | asserts output `(5,15,101,241)` |

`run_inference.py` treats `PROJECT_ROOT` as **`backend/`**.

### 3.6 Post-processing (`backend/ocean/postprocessing/`)

Removes statically unstable density inversions **per ensemble member**, then recomputes mean/std.

| File | Role | Inputs | Outputs |
| --- | --- | --- | --- |
| `eos.py` | Linear EOS `ρ = ρ0 − αT + βS` | T, S tensors (defaults ρ0=1027, α=0.15, β=0.78) | density |
| `convective_adjustment.py` | Mix adjacent inverted layers using layer thicknesses `DZ` matching the 15 depths; up to 15 passes | profiles `[N,15]`, ocean mask | adjusted T/S, inversion stats |
| `run_postprocess.py` | Chunked job (8 days) | `ensemble_member_predictions.nc`, `ocean_mask_3d.nc` | `data/physics/physics_adjusted.nc` and `physics_adjusted_member_predictions.nc` |
| `validate_physics_output.py` | Contract: time=1419, depth=15, lat=101, lon=241, required T/S mean+std | `physics_adjusted.nc` | printed validation |

`run_postprocess.py` sets `PROJECT_ROOT` to the **repo root** (`parents[3]`) and prefixes paths with `backend/`. Other ocean CLIs often use `parents[2]` = `backend/`.

### 3.7 Business products (`backend/ocean/business/`)

| File | Role | Inputs | Outputs |
| --- | --- | --- | --- |
| `tchp.py` | Heat content above 26°C; ρ=1025, Cp=3990; units kJ cm⁻² | T profile + depths | `tchp`, `d26` arrays; `add_tchp(ds)` |
| `mld.py` | Density-threshold MLD: Δρ ≤ 0.03 kg m⁻³ vs 10 m reference, using `linear_eos` | T, S, depths | `mld`; `add_mld(ds)` |
| `thermocline.py` | Depth of max \|dT/dz\| | T, depths | `thermocline_depth`; `calculate_thermocline` |
| `build_dashboard.py` | Pipeline: load physics NC → TCHP/D26 → MLD → thermocline → write | `physics_adjusted.nc` | `dashboard_ready.nc` (**output path is `PROJECT_ROOT/data/business/` with `PROJECT_ROOT` = repo root**, i.e. `inc/data/business/`, while the API reads `backend/data/business/` — copy or fix path when running this job) |
| `validate_dashboard.py` | Full-period contract (1419×15×101×241 + business vars) | `data/business/dashboard_ready.nc` under backend | printed report |
| `dashboard_export.py` | Extra validation/export helpers for the dashboard contract | datasets | encoding/validation utilities |
| `test_tchp.py`, `test_mld.py`, `test_thermocline.py` | Unit tests for the three calculators | synthetic profiles | pytest-style assertions |

TCHP categories used by the API (not stored in NetCDF): `<40` Too Low, `<60` Medium, `<90` High, else Too High.

### 3.8 Evaluation (`backend/ocean/evaluation/`)

| File | Role | Inputs | Outputs |
| --- | --- | --- | --- |
| `evaluate.py` | Streaming metrics over 8-day batches | `physics_adjusted.nc`, raw member predictions, masked T/S targets, mask | `data/evaluation/evaluation_report.json` with timestamp, depth RMSE, spatial mean RMSE, uncertainty calibration, physics inversion reduction |
| `depth_metrics.py` | RMSE/MAE at selected depths (default 0, 5, 100, 1000 m) | pred + GT datasets | nested dict |
| `spatial_metrics.py` | Accumulators over time/depth → maps of RMSE/MAE | chunks `(time,depth,lat,lon)` | lat×lon error fields + global means |
| `uncertainty_metrics.py` | Bin predicted σ vs actual error | pred, truth, std, 20 bins 0–1.5 | calibration tables |
| `physics_metrics.py` | Inversion rates raw vs adjusted | member NC + adjusted NC | % reduction stats |
| `inspect_ground_truth.py` | Print GT file existence, dims, NaN rates | evaluation dir | stdout |

The health endpoint only needs a `timestamp` field in the JSON; the evaluation route returns the whole object.

### 3.9 Utilities and sample data

| File | Role |
| --- | --- |
| `backend/ocean/data.py` | `inspect_dataset` / `inspect_all` for `backend/data/*.nc` (top-level only, not subfolders) |
| `backend/ocean/inspect_data.py` | CLI printer using `data.py` |
| `backend/ocean/inspect_raw_dates.py` | Walks `data/raw/*` and prints time coverage |
| `backend/scripts/generate_sample_dataset.py` | Writes a **3-day** synthetic `dashboard_ready.nc` (2026-08-25..27) so the UI works without production files. Uses the same eddy formulas as `mockOceanApi.ts` |

---

## 4. Frontend

**Run (repo root):**

```bash
npm install
npm run dev    # http://localhost:5173
```

`npm run build` runs `tsc -b && vite build`. `npm run preview` serves the production bundle.

### 4.1 Tooling and entry

| File | Purpose | Inputs | Outputs |
| --- | --- | --- | --- |
| `index.html` | Document title OceanEmbed, `#root` | — | Loads `/src/main.tsx` |
| `src/main.tsx` | React mount | `#root` | Renders `<App />` with MapLibre CSS + `styles.css` |
| `src/vite-env.d.ts` | Vite client types | — | — |
| `vite.config.ts` | React plugin; host `0.0.0.0`, port **5173**; proxy **`/api` → `http://127.0.0.1:8000`** | browser `/api/...` | Backend HTTP |
| `src/styles.css` | Dark operations-console theme (Inter / JetBrains Mono), layout for map, rail, depth slider, profile drawer, legend | CSS variables | Entire chrome |

### 4.2 API client (`src/api/`)

| File | Purpose |
| --- | --- |
| `types.ts` | `DEPTHS` (15 levels), `FieldId`, `Coordinate`, `FieldPoint`, `ArgoFloat`, `OceanProfile` (OceanEmbed + ARMOR3D + ARGO series), `RunStatus`, `OceanEmbedApi` |
| `apiClient.ts` | Real `fetch` to `/api/v1/ocean/*`. Maps backend profile JSON into the richer frontend `OceanProfile`. **Synthesizes ARMOR3D and ARGO comparison series** from OceanEmbed T/S with sinusoidal offsets (not from the API). Hard-codes `nearestArgoKm: 42`. Status/ARGO/field **fall back to mock** on network failure. Profile/TCHP/MLD/uncertainty **do not** mock on failure |
| `mockOceanApi.ts` | Deterministic eddy field over the 101×241 grid; crude `isLand`; same eight ARGO IDs as the backend. Used when backend is offline for map/status |

### 4.3 App shell (`src/App.tsx`)

**State:** field, depth index (default 7 → 100 m), basemap, overlay toggles, selected coordinate, field points, floats, profile, panelData, apiError, run status, analysis date (default `2026-08-25`).

**Effects:**

- On date change: `getStatus`, `getArgoFloats`, `geoService.loadMask()`.
- On date/field/depth: `getField` → map raster.
- On selection/field/depth: land → no profile; out of domain → null; else `getProfile` / `getTchp` / `getMld` / `getUncertainty`.

**UI regions:** MapLibre canvas, top bar (brand, date `<input type="date">`, MAP/SATELLITE, NRT READY badge), left rail (fields + overlays), color legend, vertical depth rail, sliding profile panel, bottom model bar (grid 0.25°, 0–1000 m, ISO week).

`showSampling` / `showSaliency` are toggled in the rail; saliency is disabled. Sampling is **not** fetched or drawn in `OceanMap` even when the switch is on.

### 4.4 Map (`src/map/`)

| File | Purpose | Inputs | Outputs |
| --- | --- | --- | --- |
| `basemaps.ts` | Raster styles | OSM tiles vs Esri World Imagery | MapLibre `StyleSpecification` |
| `OceanMap.tsx` | Map + deck.gl overlay | `points`, `floats`, overlay flags, `selected`, `onSelect` | Click → `{lat,lon}`. Raster: 241×101 `ImageData` from points, colored by field-specific stops, masked by GeoJSON land (`/land.geojson`, inverted mask so ocean shows). Grid lines at 0.25°/1°/5°. ARGO scatter. Selected-point halo. Center `[77,16]`, maxBounds around the NIO |

### 4.5 Geospatial (`src/services/GeospatialService.ts`)

**Input:** `/land.geojson` via `fetch`, plus lat/lon.  
**Output:** `isLand` (`d3-geo` `geoContains`), `isInDomain`, `getNearestModelCell`. Fallback polygons if GeoJSON has not loaded.

### 4.6 Profile panel (`src/components/profile/`)

| File | Purpose | Inputs | Outputs |
| --- | --- | --- | --- |
| `ProfilePanel.tsx` | Router for the side drawer | `field`, `profile`, `panelData`, `isOceanMissing`, `apiError` | Error / missing / TCHP / MLD / uncertainty / T-S profile views |
| `ProfileOverview.tsx` | Location + depth chart | `OceanProfile`, selected depth | Chart + legend (OceanEmbed / ARMOR3D / ARGO) |
| `ProfileChart.tsx` | SVG T or S vs depth | profile series | Clickable depth levels; solid OceanEmbed, dashed ARMOR3D, dots ARGO |
| `DepthReport.tsx` | Single-depth detail | selected depth on profile | Values + `DifferenceSection` |
| `DifferenceSection.tsx` | OceanEmbed − ARMOR3D ΔT/ΔS | numbers | Colored deltas |
| `TchpReport.tsx` | TCHP dashboard | `{value, category, d26, confidence}` | Large value, category bar (0–40–60–90–120), D26 |
| `ScalarReport.tsx` | Generic scalar (MLD, uncertainty) | title, unit, value, optional confidence/depth | Large number + metadata |

---

## 5. Environment variables and ports

| Variable | Used by | Default |
| --- | --- | --- |
| `OCEAN_DATA_DIR` | API dataset root | `backend/data` |
| `DASHBOARD_DATASET_PATH` / `OCEAN_DASHBOARD_PATH` | Dashboard NetCDF | `…/business/dashboard_ready.nc` |
| `PHYSICS_ADJUSTED_PATH` | Physics NetCDF | `…/physics/physics_adjusted.nc` |
| `EVALUATION_REPORT_PATH` / `OCEAN_EVALUATION_REPORT_PATH` | Metrics JSON | `…/evaluation/evaluation_report.json` |

| Port | Process |
| --- | --- |
| **8000** | FastAPI / uvicorn |
| **5173** | Vite dev server (proxies `/api`) |

OpenAPI: `http://localhost:8000/docs`.

---

## 6. Docker and deployment

### 6.1 What exists today

**This repository does not define Docker.** There is no `Dockerfile`, `docker-compose.yml`, `.dockerignore`, or container healthcheck. Local development is two native processes (Python + Node) as in the README.

Production note from `README.md`: large NetCDF and the model registry live on the **target system**. Copying `dashboard_ready.nc` and `evaluation_report.json` onto that host is enough for the **UI+API** path; inference does not run inside the web process.

### 6.2 How the current split would map to containers (if you add Docker)

A natural two-service layout matching the code:

**Service `backend`**

- Build context: `backend/`
- Image: Python 3.12+, `pip install -r requirements.txt`
- Command: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Publish **8000**
- Volume or bind-mount `backend/data` (and optionally `model-registry` if you run offline jobs in the same image)
- Pass the path env vars above so NetCDF is not baked into the image
- CORS currently allowlists only `http://localhost:5173` and `http://127.0.0.1:5173`. A containerized frontend on another origin needs that list updated (or a reverse proxy so the browser sees one origin)

**Service `frontend`**

- **Dev:** `npm run dev` with proxy `target: http://backend:8000` (today the proxy is hardcoded to `127.0.0.1:8000`, which **fails inside Docker** unless rewritten)
- **Prod:** `npm run build` then nginx/caddy serving `dist/`, with `/api` reverse-proxied to the backend service. That is the usual way to avoid CORS and the Vite-only proxy

**Optional batch images** (not required for the console): GPU image with PyTorch for `run_inference.py`; CPU image for acquisition/preprocess/postprocess/business/evaluate. These need Earthdata/Copernicus credentials and the model registry volume.

**`.dockerignore` (recommended if added):** `node_modules`, `dist`, `__pycache__`, `.venv`, `*.nc` if data is mounted, checkpoints.

There is no Compose `depends_on` or shared Docker network in git; you would add `backend` as a DNS name and point the frontend proxy or nginx `proxy_pass` at `http://backend:8000`.

### 6.3 Multi-system layout (as implemented)

```
Developer laptop:  Vite :5173  ──proxy──►  FastAPI :8000  ──reads──►  dashboard_ready.nc
Production host:   same binaries; replace NC/JSON (and registry if running the science jobs)
```

`generate_sample_dataset.py` exists specifically so the frontend can be integrated without the 1419-day production cube.

---

## 7. Frontend ↔ backend contract cheat sheet

| UI action | Client call | Backend route | NetCDF variables |
| --- | --- | --- | --- |
| Load map | `getField(date, field, depth)` | `/field?variable=&date=&depth=` | see field map in §3.2 |
| Status badge | `getStatus` | `/health` | time coords + evaluation timestamp |
| ARGO dots | `getArgoFloats` | `/argo` | none (static list) |
| Click T/S | `getProfile` | `/profile?date&lat&lon` | T/S mean+std, tchp, d26, mld, thermocline_depth |
| Click TCHP | `getTchp` | `/tchp` | tchp, d26 |
| Click MLD | `getMld` | `/mld` | mld |
| Click uncertainty | `getUncertainty` | `/uncertainty?...&depth=` | temperature_std, salinity_std |
| (unused in UI) | `getD26`, `getEvaluationReport` | `/d26`, `/evaluation` | d26; JSON file |
| (unused in UI) | — | `/sampling`, `/thermocline`, `/metadata` | stds / thermocline / summary |

---

## 8. Typical operator commands

From `backend/` (venv with `requirements.txt`; extra tools `copernicusmarine`, `podaac-data-downloader`, `xesmf` for full pipeline):

```text
python -m ocean.acquisition.download_all
python -m ocean.inference.validate_input
python -m ocean.inference.validate_models
python -m ocean.inference.run_inference
python -m ocean.postprocessing.run_postprocess
python -m ocean.business.build_dashboard
python -m ocean.evaluation.evaluate
python scripts/generate_sample_dataset.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

From repo root: `npm run dev`.

---

## 9. Gaps and integration notes

- **No Docker files** in the repo; do not assume `docker compose up` works until they are added.
- **`/land.geojson`** is required for accurate land masking in the map and click handler; it is not in this tree.
- **ARGO** is a static demo list, not live GDAC positions.
- **ARMOR3D / ARGO profile overlays** in the chart are generated in `apiClient.ts`, not served by FastAPI (`profile.py` even states ARGO and ARMOR3D are unused).
- **Sampling and saliency** UI switches do not load `/sampling` or a saliency endpoint.
- **Exception handlers** in `errors.py` are unused; many routes raise raw `HTTPException` or unhandled `DataNotAvailableError`.
- **Path roots differ** between jobs (`parents[2]` vs `parents[3]`); `build_dashboard.py` currently writes `dashboard_ready.nc` under repo-root `data/business/` while the API reads `backend/data/business/`.
- **`evaluation_report.json` in this working tree** may not match the schema written by `evaluate.py` (the evaluator writes `timestamp`, `depth_metrics`, `spatial_metrics_summary`, etc.). The health route only uses `timestamp` when present.
- **CORS** is localhost-Vite only; production behind a single reverse proxy is the robust fix.

This is the complete map of how OceanEmbed’s science jobs, REST API, and operations console fit together, and how containers would wrap that split even though Docker is not configured in the repository today.
