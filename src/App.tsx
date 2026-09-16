import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { oceanApi } from "./api/apiClient";
import { DEPTHS, type ArgoFloat, type Coordinate, type FieldId, type FieldPoint, type OceanProfile, type RunStatus } from "./api/types";
import { OceanMap } from "./map/OceanMap";
import type { BasemapId } from "./map/basemaps";
import { CalendarControl } from "./components/CalendarControl";
import { BasemapToggle } from "./components/BasemapToggle";
import { DepthControl } from "./components/depth/DepthControl";
import { SimulationPlayer } from "./components/simulation/SimulationPlayer";
import type { SelectedLocation, GraphCardCluster } from "./types/comparison";
import { LOCATION_LABELS, LOCATION_COLORS, MAX_LOCATIONS } from "./types/comparison";
import { geoService } from "./services/GeospatialService";

const fieldDefinitions: { id: FieldId; label: string; unit: string; depth: boolean; color: string; short: string }[] = [
  { id: "temperature", label: "Temperature", unit: "°C", depth: true, color: "#FF9B5E", short: "OSTS" },
  { id: "salinity", label: "Salinity", unit: "psu", depth: true, color: "#58A6FF", short: "OSSS" },
  { id: "uncertainty", label: "Uncertainty", unit: "σ °C", depth: true, color: "#B8C4CC", short: "σ" },
  { id: "tchp", label: "Cyclone heat", unit: "kJ cm⁻²", depth: false, color: "#FF5C63", short: "TCHP" },
  { id: "mld", label: "Mixed-layer depth", unit: "m", depth: false, color: "#A98BFF", short: "MLD" },
];

export function App() {
  const [field, setField] = useState<FieldId>("temperature");
  const [depthIndex, setDepthIndex] = useState(7);
  const [basemap, setBasemap] = useState<BasemapId>("basic");
  
  const [railOpen, setRailOpen] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [showArgo, setShowArgo] = useState(true);
  const [showSampling, setShowSampling] = useState(false);
  const [showSaliency, setShowSaliency] = useState(false);
  
  // Multi-location selection & floating card cluster state
  const [selectedLocations, setSelectedLocations] = useState<SelectedLocation[]>([]);
  const [clusters, setClusters] = useState<GraphCardCluster[]>([]);
  const [justMergedClusterId, setJustMergedClusterId] = useState<string | null>(null);
  const [maxToast, setMaxToast] = useState(false);
  const toastTimeoutRef = useRef<number | null>(null);

  // Simulation player state
  const [isSimulating, setIsSimulating] = useState(false);
  const [simStartDate, setSimStartDate] = useState("2026-08-20");
  const [simEndDate, setSimEndDate] = useState("2026-08-27");
  const [isPlayingSim, setIsPlayingSim] = useState(false);
  const [simSpeed, setSimSpeed] = useState(1); // 1x, 2x, 10x, 20x
  const [simLoop, setSimLoop] = useState(true);

  const [points, setPoints] = useState<FieldPoint[]>([]);
  const [floats, setFloats] = useState<ArgoFloat[]>([]);
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

  // Track ongoing profile fetches to prevent duplicate/cascading in-flight requests
  const fetchingProfilesRef = useRef<Record<string, string>>({});

  // Load profiles for each selected location with cancellation of obsolete requests
  useEffect(() => {
    let isCurrent = true;
    const targetDate = selectedAnalysisDate;

    selectedLocations.forEach((loc) => {
      const hasCorrectWeek = loc.profile && loc.profile.week === targetDate;
      const isAlreadyFetching = fetchingProfilesRef.current[loc.id] === targetDate;

      if (hasCorrectWeek || isAlreadyFetching) {
        return;
      }

      if (!geoService.isLand(loc.coord.lat, loc.coord.lon) && geoService.isInDomain(loc.coord.lat, loc.coord.lon)) {
        fetchingProfilesRef.current[loc.id] = targetDate;

        oceanApi.getProfile(targetDate, loc.coord)
          .then((prof) => {
            delete fetchingProfilesRef.current[loc.id];
            if (!isCurrent) return; // Discard obsolete in-flight requests from earlier simulation dates
            setSelectedLocations((prev) =>
              prev.map((item) =>
                item.id === loc.id ? { ...item, profile: prof ? { ...prof, week: targetDate } : null, loading: false } : item
              )
            );
          })
          .catch((err) => {
            delete fetchingProfilesRef.current[loc.id];
            if (!isCurrent) return;
            console.error("Failed to load profile for location", loc.label, err);
            setSelectedLocations((prev) =>
              prev.map((item) =>
                item.id === loc.id ? { ...item, loading: false } : item
              )
            );
          });
      }
    });

    return () => {
      isCurrent = false;
    };
  }, [selectedLocations, selectedAnalysisDate]);

  // If single location selected and field is scalar, load scalar panelData
  const singleLocation = selectedLocations.length === 1 ? selectedLocations[0] : null;
  useEffect(() => {
    let isCurrent = true;
    if (!singleLocation) {
      setPanelData(undefined);
      return;
    }
    const coord = singleLocation.coord;
    if (geoService.isLand(coord.lat, coord.lon) || !geoService.isInDomain(coord.lat, coord.lon)) {
      setPanelData(null);
      return;
    }

    const targetDate = selectedAnalysisDate;
    if (field === 'tchp') {
      oceanApi.getTchp(targetDate, coord)
        .then((res) => { if (isCurrent) setPanelData(res); })
        .catch(() => { if (isCurrent) setPanelData(null); });
    } else if (field === 'mld') {
      oceanApi.getMld(targetDate, coord)
        .then((res) => { if (isCurrent) setPanelData(res); })
        .catch(() => { if (isCurrent) setPanelData(null); });
    } else if (field === 'uncertainty') {
      oceanApi.getUncertainty(targetDate, coord, depth)
        .then((res) => { if (isCurrent) setPanelData(res); })
        .catch(() => { if (isCurrent) setPanelData(null); });
    } else {
      setPanelData(undefined);
    }

    return () => {
      isCurrent = false;
    };
  }, [singleLocation, selectedAnalysisDate, field, depth]);

  // List of all dates in the selected simulation range
  const simDatesList = useMemo(() => {
    const list: string[] = [];
    const curr = new Date(simStartDate);
    const end = new Date(simEndDate);
    if (isNaN(curr.getTime()) || isNaN(end.getTime()) || curr > end) {
      return [simStartDate];
    }
    // Allow full multi-year simulation ranges (safety ceiling of 10 years / 3652 days)
    while (curr <= end && list.length < 3652) {
      list.push(curr.toISOString().split("T")[0]);
      curr.setDate(curr.getDate() + 1);
    }
    return list;
  }, [simStartDate, simEndDate]);

  // Simulation playback forward step
  const handleStepForwardSim = useCallback(() => {
    setSelectedAnalysisDate((prevDate) => {
      const idx = simDatesList.indexOf(prevDate);
      if (idx === -1) {
        return simDatesList[0] || prevDate;
      }
      if (idx < simDatesList.length - 1) {
        return simDatesList[idx + 1];
      }
      if (simLoop) {
        return simDatesList[0];
      }
      setIsPlayingSim(false);
      return prevDate;
    });
  }, [simDatesList, simLoop]);

  // Simulation playback backward step
  const handleStepBackwardSim = useCallback(() => {
    setSelectedAnalysisDate((prevDate) => {
      const idx = simDatesList.indexOf(prevDate);
      if (idx === -1) {
        return simDatesList[0] || prevDate;
      }
      if (idx > 0) {
        return simDatesList[idx - 1];
      }
      if (simLoop) {
        return simDatesList[simDatesList.length - 1];
      }
      return prevDate;
    });
  }, [simDatesList, simLoop]);

  // Simulation timer playback interval
  useEffect(() => {
    if (!isSimulating || !isPlayingSim) return;
    const intervalMs = Math.round(1100 / simSpeed);
    const timer = window.setInterval(() => {
      handleStepForwardSim();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [isSimulating, isPlayingSim, simSpeed, handleStepForwardSim]);

  const handleStartSimulation = useCallback((start: string, end: string) => {
    setSimStartDate(start);
    setSimEndDate(end);
    setSelectedAnalysisDate(start);
    setIsSimulating(true);
    setIsPlayingSim(true);
  }, []);

  const handleCloseSimulation = useCallback(() => {
    setIsSimulating(false);
    setIsPlayingSim(false);
  }, []);

  // Clear all locations and clusters
  const handleClearAllLocations = useCallback(() => {
    setSelectedLocations([]);
    setClusters([]);
  }, []);

  // Remove location handler
  const handleRemoveLocation = useCallback((id: string) => {
    setSelectedLocations((prev) => prev.filter((item) => item.id !== id));
    setClusters((prev) =>
      prev
        .map((c) => {
          const remaining = c.locationIds.filter((lid) => lid !== id);
          return {
            ...c,
            locationIds: remaining,
            isMerged: remaining.length >= 2,
          };
        })
        .filter((c) => c.locationIds.length > 0)
    );
  }, []);

  // Remove entire cluster card
  const handleRemoveCluster = useCallback((clusterId: string) => {
    setClusters((prev) => {
      const cluster = prev.find((c) => c.id === clusterId);
      if (cluster) {
        setSelectedLocations((sPrev) =>
          sPrev.filter((loc) => !cluster.locationIds.includes(loc.id))
        );
      }
      return prev.filter((c) => c.id !== clusterId);
    });
  }, []);

  // Handle map coordinate clicks (add or toggle location)
  const handleSelectCoordinate = useCallback((coord: Coordinate) => {
    // 1. Check if clicking on or near an existing selected location (within ~0.35 degrees)
    const existingIndex = selectedLocations.findIndex(
      (loc) => Math.hypot(loc.coord.lat - coord.lat, loc.coord.lon - coord.lon) < 0.35
    );

    if (existingIndex >= 0) {
      // Toggle off / remove
      const toRemove = selectedLocations[existingIndex];
      handleRemoveLocation(toRemove.id);
      return;
    }

    // 2. Enforce Maximum 6 locations limit
    if (selectedLocations.length >= MAX_LOCATIONS) {
      setMaxToast(true);
      if (toastTimeoutRef.current) window.clearTimeout(toastTimeoutRef.current);
      toastTimeoutRef.current = window.setTimeout(() => setMaxToast(false), 2500);
      return;
    }

    // 3. Allocate next unused letter identifier (A, B, C, D, E, F)
    const usedLabels = new Set(selectedLocations.map((l) => l.label));
    const nextLabel = LOCATION_LABELS.find((lbl) => !usedLabels.has(lbl)) || "A";
    const labelIdx = LOCATION_LABELS.indexOf(nextLabel);
    const color = LOCATION_COLORS[labelIdx >= 0 ? labelIdx : 0];

    const newLoc: SelectedLocation = {
      id: `loc_${coord.lat.toFixed(4)}_${coord.lon.toFixed(4)}_${Date.now()}`,
      label: nextLabel,
      coord,
      color,
      inComparison: false,
      profile: null,
      loading: true,
    };

    setSelectedLocations((prev) => [...prev, newLoc]);

    // Intelligent stagger offsets so cards don't overlap initially
    const staggerOffsets = [
      { x: 35, y: -70 },
      { x: 50, y: 50 },
      { x: -340, y: -70 },
      { x: -340, y: 50 },
      { x: 40, y: -210 },
      { x: -340, y: -210 },
    ];
    const offset = staggerOffsets[selectedLocations.length % staggerOffsets.length];

    const newCluster: GraphCardCluster = {
      id: `cluster_${newLoc.id}`,
      locationIds: [newLoc.id],
      offset,
      isMerged: false,
    };

    setClusters((prev) => [...prev, newCluster]);
  }, [selectedLocations, handleRemoveLocation]);

  // Merge clusters handler (when dragging graph A onto graph B)
  const handleMergeClusters = useCallback((sourceClusterId: string, targetClusterId: string) => {
    if (sourceClusterId === targetClusterId) return;

    setClusters((prev) => {
      const source = prev.find((c) => c.id === sourceClusterId);
      const target = prev.find((c) => c.id === targetClusterId);
      if (!source || !target) return prev;

      const mergedLocationIds = Array.from(
        new Set([...target.locationIds, ...source.locationIds])
      );

      return prev
        .filter((c) => c.id !== sourceClusterId)
        .map((c) =>
          c.id === targetClusterId
            ? { ...c, locationIds: mergedLocationIds, isMerged: true }
            : c
        );
    });

    // Play merge pulse animation on the target card
    setJustMergedClusterId(targetClusterId);
    window.setTimeout(() => setJustMergedClusterId(null), 500);
  }, []);

  // Split all locations in a merged cluster back into individual cards
  const handleSplitCluster = useCallback((clusterId: string) => {
    setClusters((prev) => {
      const cluster = prev.find((c) => c.id === clusterId);
      if (!cluster) return prev;

      const remaining = prev.filter((c) => c.id !== clusterId);
      const newClusters: GraphCardCluster[] = cluster.locationIds.map((locId, i) => ({
        id: `cluster_${locId}_${Date.now()}_${i}`,
        locationIds: [locId],
        offset: {
          x: cluster.offset.x + (i % 2 === 0 ? 30 : -340),
          y: cluster.offset.y + Math.floor(i / 2) * 80,
        },
        isMerged: false,
      }));

      return [...remaining, ...newClusters];
    });
  }, []);

  // Detach a single location from a merged cluster
  const handleDetachLocation = useCallback((clusterId: string, locId: string) => {
    setClusters((prev) => {
      const cluster = prev.find((c) => c.id === clusterId);
      if (!cluster) return prev;

      const remainingLocIds = cluster.locationIds.filter((id) => id !== locId);
      const updatedCluster: GraphCardCluster = {
        ...cluster,
        locationIds: remainingLocIds,
        isMerged: remainingLocIds.length >= 2,
      };

      const detachedCluster: GraphCardCluster = {
        id: `cluster_${locId}_${Date.now()}`,
        locationIds: [locId],
        offset: { x: cluster.offset.x + 60, y: cluster.offset.y + 40 },
        isMerged: false,
      };

      return [
        ...prev.filter((c) => c.id !== clusterId),
        updatedCluster,
        detachedCluster,
      ];
    });
  }, []);

  // Update card offset on drag
  const handleUpdateClusterOffset = useCallback(
    (clusterId: string, offset: { x: number; y: number }) => {
      setClusters((prev) =>
        prev.map((c) => (c.id === clusterId ? { ...c, offset } : c))
      );
    },
    []
  );

  return (
    <>
      {/* Maximum 6 Locations Alert Toast */}
      {maxToast && (
        <div className="max-locations-toast">
          MAXIMUM 6 LOCATIONS
        </div>
      )}

      <div className="map-canvas">
        <OceanMap 
          basemap={basemap} 
          field={field} 
          points={points} 
          floats={floats} 
          showGrid={showGrid} 
          showArgo={showArgo} 
          showSampling={showSampling} 
          showSaliency={showSaliency} 
          selectedLocations={selectedLocations}
          clusters={clusters}
          onSelect={handleSelectCoordinate}
          onToggleLocation={(loc) => handleRemoveLocation(loc.id)}
          date={selectedAnalysisDate}
          fieldLabel={selectedField.label}
          fieldUnit={selectedField.unit}
          isDepthField={selectedField.depth}
          depth={depth}
          panelData={panelData}
          apiError={apiError}
          justMergedClusterId={justMergedClusterId}
          onMergeClusters={handleMergeClusters}
          onSplitCluster={handleSplitCluster}
          onDetachLocation={handleDetachLocation}
          onRemoveCluster={handleRemoveCluster}
          onRemoveLocation={handleRemoveLocation}
          onClearAllLocations={handleClearAllLocations}
          onUpdateClusterOffset={handleUpdateClusterOffset}
        />
      </div>

      <CalendarControl
        date={selectedAnalysisDate}
        onSelectDate={setSelectedAnalysisDate}
        onStartSimulation={handleStartSimulation}
        isSimulating={isSimulating}
        simulationRange={{ startDate: simStartDate, endDate: simEndDate }}
      />

      {isSimulating && (
        <SimulationPlayer
          startDate={simStartDate}
          endDate={simEndDate}
          currentDate={selectedAnalysisDate}
          isPlaying={isPlayingSim}
          speed={simSpeed}
          loop={simLoop}
          onTogglePlay={() => setIsPlayingSim((prev) => !prev)}
          onStepForward={handleStepForwardSim}
          onStepBackward={handleStepBackwardSim}
          onSeekDate={setSelectedAnalysisDate}
          onChangeSpeed={setSimSpeed}
          onToggleLoop={() => setSimLoop((prev) => !prev)}
          onClose={handleCloseSimulation}
        />
      )}

      {selectedLocations.length > 0 && (
        <button
          type="button"
          className="bottom-clear-btn"
          onClick={handleClearAllLocations}
          title={`Clear all selected locations (${selectedLocations.length})`}
          aria-label="Clear all selected locations"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
          <span className="bottom-clear-badge">{selectedLocations.length}</span>
        </button>
      )}

      <BasemapToggle
        basemap={basemap}
        onChangeBasemap={setBasemap}
      />

      {/* COLLAPSIBLE LAYER RAIL */}
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
            if (field !== item.id) {
              setField(item.id);
              setPanelData(undefined);
            }
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

      {/* FIELD SCALE / LEGEND */}
      <div className="legend" role="region" aria-label="Field Color Scale">
        <div className="ttl">{selectedField.label} — {selectedField.depth ? `${depth}m` : "Surface"}</div>
        <div className={`bar ${field}`}></div>
        <div className="scale">
          <span>{selectedField.unit}</span>
        </div>
      </div>

      {/* ERGONOMIC FLOATING DEPTH CONTROL */}
      <DepthControl
        depthIndex={depthIndex}
        onChangeDepthIndex={setDepthIndex}
        isDepthField={selectedField.depth}
        fieldLabel={selectedField.label}
      />
    </>
  );
}
