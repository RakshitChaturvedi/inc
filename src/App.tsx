import { useCallback, useEffect, useMemo, useState } from "react";
import { oceanApi } from "./api/apiClient";
import { DEPTHS, type ArgoFloat, type Coordinate, type FieldId, type FieldPoint, type OceanProfile, type RunStatus } from "./api/types";
import { OceanMap } from "./map/OceanMap";
import { ProfilePanel } from "./components/profile/ProfilePanel";
import type { BasemapId } from "./map/basemaps";
import { CalendarControl } from "./components/CalendarControl";
import { BasemapToggle } from "./components/BasemapToggle";

const fieldDefinitions: { id: FieldId; label: string; unit: string; depth: boolean; color: string; short: string }[] = [
  { id: "temperature", label: "Temperature", unit: "°C", depth: true, color: "#FF9B5E", short: "OSTS" },
  { id: "salinity", label: "Salinity", unit: "psu", depth: true, color: "#58A6FF", short: "OSSS" },
  { id: "uncertainty", label: "Uncertainty", unit: "σ °C", depth: true, color: "#B8C4CC", short: "σ" },
  { id: "tchp", label: "Cyclone heat", unit: "kJ cm⁻²", depth: false, color: "#FF5C63", short: "TCHP" },
  { id: "mld", label: "Mixed-layer depth", unit: "m", depth: false, color: "#A98BFF", short: "MLD" },
];

import { geoService } from "./services/GeospatialService";

function formatLocation(location?: Coordinate) {
  if (!location) return "No location selected";
  return `${location.lat.toFixed(2)}°N, ${location.lon.toFixed(2)}°E`;
}

function regionName(lat: number, lon: number) {
  if (lon < 60) return "Western Arabian Sea";
  if (lon < 77) return "Eastern Arabian Sea";
  if (lon < 85 && lat < 15) return "Southern tip / approach to Bay";
  return "Central Bay of Bengal";
}

export function App() {
  const [field, setField] = useState<FieldId>("temperature");
  const [depthIndex, setDepthIndex] = useState(7);
  const [basemap, setBasemap] = useState<BasemapId>("basic");
  
  const [railOpen, setRailOpen] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [showArgo, setShowArgo] = useState(true);
  const [showSampling, setShowSampling] = useState(false);
  const [showSaliency, setShowSaliency] = useState(false);
  
  const [selected, setSelected] = useState<Coordinate | null>(null);
  
  const [points, setPoints] = useState<FieldPoint[]>([]);
  const [floats, setFloats] = useState<ArgoFloat[]>([]);
  const [profile, setProfile] = useState<OceanProfile | null | undefined>();
  const [panelData, setPanelData] = useState<any>();
  const [apiError, setApiError] = useState<string | null>(null);
  const [status, setStatus] = useState<RunStatus>();
  const [selectedAnalysisDate, setSelectedAnalysisDate] = useState("2026-08-25");
  
  const selectedField = useMemo(() => fieldDefinitions.find((item) => item.id === field)!, [field]);
  const depth = DEPTHS[depthIndex];

  useEffect(() => {
    setApiError(null);
    const controller = new AbortController();
    oceanApi.getStatus(selectedAnalysisDate).then(data => { if (!controller.signal.aborted) setStatus(data); }).catch(e => { if (!controller.signal.aborted) console.error(e); });
    oceanApi.getArgoFloats(selectedAnalysisDate).then(data => { if (!controller.signal.aborted) setFloats(data); }).catch(e => { if (!controller.signal.aborted) console.error(e); });
    geoService.loadMask();
    return () => controller.abort();
  }, [selectedAnalysisDate]);
  
  useEffect(() => { 
    const controller = new AbortController();
    void oceanApi.getField(selectedAnalysisDate, field, selectedField.depth ? depth : 0).then(data => {
      if (!controller.signal.aborted) setPoints(data);
    }).catch(err => {
      if (!controller.signal.aborted) console.error("Failed to load map field", err);
    }); 
    return () => controller.abort();
  }, [selectedAnalysisDate, field, depth, selectedField.depth]);
  
  useEffect(() => { 
    const controller = new AbortController();
    setApiError(null);
    
    if (selected) {
      if (geoService.isLand(selected.lat, selected.lon)) {
        setProfile(undefined);
        setPanelData(undefined);
      } else if (!geoService.isInDomain(selected.lat, selected.lon)) {
        setProfile(null);
        setPanelData(null);
      } else {
        const handleSuccess = (setData: (v: any) => void) => (data: any) => {
          if (!controller.signal.aborted) setData(data);
        };
        const handleError = (err: any) => {
          if (!controller.signal.aborted) {
            setApiError(err.message || "Failed to load profile data");
            setProfile(null);
            setPanelData(null);
          }
        };

        if (field === 'temperature' || field === 'salinity') {
          setPanelData(undefined);
          void oceanApi.getProfile(selectedAnalysisDate, selected)
            .then(handleSuccess(setProfile)).catch(handleError);
        } else if (field === 'tchp') {
          setPanelData(undefined);
          setProfile(undefined);
          void oceanApi.getTchp(selectedAnalysisDate, selected)
            .then(handleSuccess(setPanelData)).catch(handleError);
        } else if (field === 'mld') {
          setPanelData(undefined);
          setProfile(undefined);
          void oceanApi.getMld(selectedAnalysisDate, selected)
            .then(handleSuccess(setPanelData)).catch(handleError);
        } else if (field === 'uncertainty') {
          setPanelData(undefined);
          setProfile(undefined);
          void oceanApi.getUncertainty(selectedAnalysisDate, selected, depth)
            .then(handleSuccess(setPanelData)).catch(handleError);
        }
      }
    } else {
      setProfile(undefined);
      setPanelData(undefined);
    }
    
    return () => controller.abort();
  }, [selected, selectedAnalysisDate, field, depth]);

  const chooseLocation = useCallback((location: Coordinate) => setSelected(location), []);

  return (
    <>
      <div className="map-canvas">
        <OceanMap basemap={basemap} field={field} points={points} floats={floats} showGrid={showGrid} showArgo={showArgo} showSampling={showSampling} showSaliency={showSaliency} selected={selected ?? undefined} onSelect={chooseLocation} />
      </div>
      
      <CalendarControl
        date={selectedAnalysisDate}
        onSelectDate={setSelectedAnalysisDate}
      />

      <BasemapToggle
        basemap={basemap}
        onChangeBasemap={setBasemap}
      />

      <div className={`rail ${railOpen ? "open" : ""}`}>
        <div className="rail-toggle" onClick={() => setRailOpen(!railOpen)} title={railOpen ? "Collapse control panel" : "Expand control panel"}>
          <svg
            className="rail-toggle-chevron"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#42E8D4"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          <span className="rail-toggle-text">{railOpen ? "COLLAPSE" : "EXPAND"}</span>
        </div>
        
        <div className="rail-section-label">RECONSTRUCTED FIELDS</div>
        {fieldDefinitions.map((item) => (
          <div key={item.id} className={`layer-btn ${field === item.id ? "active" : ""}`} onClick={() => {
            setField(item.id);
            setProfile(undefined);
            setPanelData(undefined);
          }} data-name={item.label} data-short={item.short}>
            <span className="swatch" style={{ background: item.color }}></span>
            <span className="lbl">{item.label}</span>
            <span className="num">{item.short}</span>
          </div>
        ))}
        
        <div className="rail-divider"></div>
        <div className="rail-section-label">OVERLAYS</div>
        
        <div className={`toggle-row ${showGrid ? "active" : ""}`} onClick={() => setShowGrid(!showGrid)} data-name="0.25° Model Grid">
          <svg className="toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="3" y1="15" x2="21" y2="15"></line>
            <line x1="9" y1="3" x2="9" y2="21"></line>
            <line x1="15" y1="3" x2="15" y2="21"></line>
          </svg>
          <span className="t-lbl">0.25° Model Grid</span>
          <div className={`switch ${showGrid ? "on" : ""}`}></div>
        </div>
        <div className={`toggle-row ${showArgo ? "active" : ""}`} onClick={() => setShowArgo(!showArgo)} data-name="ARGO floats">
          <svg className="toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
            <circle cx="12" cy="10" r="3"></circle>
          </svg>
          <span className="t-lbl">ARGO floats</span>
          <div className={`switch ${showArgo ? "on" : ""}`}></div>
        </div>
        <div className={`toggle-row ${showSampling ? "active" : ""}`} onClick={() => setShowSampling(!showSampling)} data-name="Suggested sampling">
          <svg className="toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="22" y1="12" x2="18" y2="12"></line>
            <line x1="6" y1="12" x2="2" y2="12"></line>
            <line x1="12" y1="6" x2="12" y2="2"></line>
            <line x1="12" y1="22" x2="12" y2="18"></line>
          </svg>
          <span className="t-lbl">Suggested sampling</span>
          <div className={`switch ${showSampling ? "on" : ""}`}></div>
        </div>
        <div className="toggle-row disabled" data-name="Saliency (future)">
          <svg className="toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          <span className="t-lbl">Saliency (future)</span>
          <div className="switch"></div>
        </div>
      </div>

      <div className="legend">
        <div className="ttl">{selectedField.label} — {selectedField.depth ? `${depth}m` : "Surface"}</div>
        <div className={`bar ${field}`}></div>
        <div className="scale">
          <span>{selectedField.unit}</span>
        </div>
      </div>

      <div className={`depth-rail ${!selectedField.depth ? "muted" : ""}`}>
        <div className="cap">Depth</div>
        <div className="depth-track-wrap">
          <div className="depth-track"></div>
          {DEPTHS.map((d, i) => (
            <div key={d} className="depth-tick" style={{ top: `${(i / (DEPTHS.length - 1)) * 100}%` }}>
              <div className="mk"></div>
              <div className="lb">{d}m</div>
            </div>
          ))}
          <div className="depth-handle" style={{ top: `${(depthIndex / (DEPTHS.length - 1)) * 100}%` }}></div>
          <div 
            style={{ position: 'absolute', inset: 0, cursor: 'pointer', zIndex: 10 }}
            onClick={(e) => {
              if (!selectedField.depth) return;
              const rect = e.currentTarget.getBoundingClientRect();
              const t = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
              const idx = Math.round(t * (DEPTHS.length - 1));
              setDepthIndex(idx);
            }}
          />
        </div>
        <div className="depth-readout">
          <div className="val">{depth}</div>
          <div className="unit">METERS</div>
        </div>
      </div>

      <div className={`profile-panel ${selected ? "show" : ""}`}>
        <div className="pp-close" style={{ zIndex: 50, pointerEvents: 'auto' }} onClick={(e) => { e.stopPropagation(); setSelected(null); }}>✕</div>
        <div className="pp-head">
          <div className="coord">
            {selected
              ? geoService.isLand(selected.lat, selected.lon)
                ? `⛰️ LAND · ${formatLocation(selected)}`
                : !geoService.isInDomain(selected.lat, selected.lon)
                ? `🌐 OUT OF DOMAIN · ${formatLocation(selected)}`
                : `🌊 OCEAN · ${formatLocation(selected)}`
              : "No location selected"}
          </div>
          <div className="region">
            {selected && geoService.isLand(selected.lat, selected.lon)
              ? "Land Mass (Subsurface Profile N/A)"
              : selected && !geoService.isInDomain(selected.lat, selected.lon)
              ? "Outside Model Domain (5°N–30°N, 45°E–105°E)"
              : `${status?.analysisWeek ?? "—"} · nearest ARGO ${profile?.nearestArgoKm ? `${profile.nearestArgoKm.toFixed(0)} km` : "—"}`}
          </div>
        </div>
        <div className="pp-body" style={{ height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
          {selected && geoService.isLand(selected.lat, selected.lon) ? (
            <div className="land-warning-card" style={{ padding: "36px 20px", textAlign: "center", background: "rgba(255, 122, 82, 0.06)", border: "1px dashed rgba(255, 122, 82, 0.4)", borderRadius: "10px", margin: "10px 0" }}>
              <div style={{ fontSize: "28px", marginBottom: "8px" }}>⛰️</div>
              <b style={{ fontSize: "14px", color: "#ff7a52", letterSpacing: "0.05em" }}>LAND LOCATION SELECTED</b>
              <p style={{ fontSize: "12px", marginTop: "10px", color: "#a0b0b8", lineHeight: "1.5" }}>
                Coordinate <strong>{formatLocation(selected)}</strong> is on land mass. Subsurface ocean profiles (0–1000m) are only computed for water cells.
              </p>
            </div>
          ) : selected && !geoService.isInDomain(selected.lat, selected.lon) ? (
            <div className="land-warning-card" style={{ padding: "36px 20px", textAlign: "center", background: "rgba(255, 180, 0, 0.06)", border: "1px dashed rgba(255, 180, 0, 0.4)", borderRadius: "10px", margin: "10px 0" }}>
              <div style={{ fontSize: "28px", marginBottom: "8px" }}>🌐</div>
              <b style={{ fontSize: "14px", color: "#ffb400", letterSpacing: "0.05em" }}>OUTSIDE MODEL DOMAIN</b>
              <p style={{ fontSize: "12px", marginTop: "10px", color: "#a0b0b8", lineHeight: "1.5" }}>
                Coordinate <strong>{formatLocation(selected)}</strong> is outside the OceanEmbed domain (5.0°N–30.0°N, 45.0°E–105.0°E). Reconstructed subsurface fields and metrics are only computed within this coverage box.
              </p>
            </div>
          ) : (
            <ProfilePanel 
              field={field} 
              profile={profile ?? null} 
              panelData={panelData ?? null} 
              isOceanMissing={(field === 'temperature' || field === 'salinity') ? profile === null : panelData === null} 
              apiError={apiError} 
            />
          )}
        </div>
      </div>

      <div className="bottom-model-bar">
        <div className="bmb-brand">
          <div className="bmb-pulse-dot"></div>
          <span className="bmb-model-name">OCEANEMBED</span>
          <span className="bmb-chip">CBAM-CNN · v1.0.0</span>
        </div>
        <div className="bmb-sep"></div>
        <div className="bmb-subtitle">
          Convolutional Block Attention Reanalysis
        </div>
        <div className="bmb-sep"></div>
        <div className="bmb-specs">
          <span className="bmb-spec-item"><b>GRID:</b> 0.25° × 0.25°</span>
          <span className="bmb-spec-dot">·</span>
          <span className="bmb-spec-item"><b>DEPTH:</b> 0–1000m</span>
          <span className="bmb-spec-dot">·</span>
          <span className="bmb-spec-item"><b>CYCLE:</b> {status?.analysisWeek ?? "2026-W35"}</span>
        </div>
      </div>

    </>
  );
}
