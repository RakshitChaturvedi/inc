import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { oceanApi } from "./api/apiClient";
import { DEPTHS, type ArgoFloat, type Coordinate, type FieldId, type FieldPoint, type OceanProfile, type RunStatus } from "./api/types";
import { OceanMap } from "./map/OceanMap";
import type { BasemapId } from "./map/basemaps";
import { CalendarControl } from "./components/CalendarControl";
import { BasemapToggle } from "./components/BasemapToggle";
import { WindyLayerDock, WINDY_FIELDS } from "./components/windy/WindyLayerDock";
import { WindyMenuDrawer } from "./components/windy/WindyMenuDrawer";
import type { SelectedLocation, GraphCardCluster } from "./types/comparison";
import { LOCATION_LABELS, LOCATION_COLORS, MAX_LOCATIONS } from "./types/comparison";
import { geoService } from "./services/GeospatialService";

const fieldDefinitions = WINDY_FIELDS;

export function App() {
  const [field, setField] = useState<FieldId>("temperature");
  const [depthIndex, setDepthIndex] = useState(7);
  const [basemap, setBasemap] = useState<BasemapId>("basic");
  
  const [menuOpen, setMenuOpen] = useState(false);
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

  // Load profiles for each selected location
  useEffect(() => {
    selectedLocations.forEach((loc) => {
      if (loc.profile === null && !geoService.isLand(loc.coord.lat, loc.coord.lon) && geoService.isInDomain(loc.coord.lat, loc.coord.lon)) {
        oceanApi.getProfile(selectedAnalysisDate, loc.coord)
          .then((prof) => {
            setSelectedLocations((prev) =>
              prev.map((item) =>
                item.id === loc.id ? { ...item, profile: prof, loading: false } : item
              )
            );
          })
          .catch((err) => {
            console.error("Failed to load profile for location", loc.label, err);
            setSelectedLocations((prev) =>
              prev.map((item) =>
                item.id === loc.id ? { ...item, loading: false } : item
              )
            );
          });
      }
    });
  }, [selectedLocations, selectedAnalysisDate]);

  // If single location selected and field is scalar, load scalar panelData
  const singleLocation = selectedLocations.length === 1 ? selectedLocations[0] : null;
  useEffect(() => {
    if (!singleLocation) {
      setPanelData(undefined);
      return;
    }
    const coord = singleLocation.coord;
    if (geoService.isLand(coord.lat, coord.lon) || !geoService.isInDomain(coord.lat, coord.lon)) {
      setPanelData(null);
      return;
    }

    if (field === 'tchp') {
      oceanApi.getTchp(selectedAnalysisDate, coord).then(setPanelData).catch(() => setPanelData(null));
    } else if (field === 'mld') {
      oceanApi.getMld(selectedAnalysisDate, coord).then(setPanelData).catch(() => setPanelData(null));
    } else if (field === 'uncertainty') {
      oceanApi.getUncertainty(selectedAnalysisDate, coord, depth).then(setPanelData).catch(() => setPanelData(null));
    } else {
      setPanelData(undefined);
    }
  }, [singleLocation, selectedAnalysisDate, field, depth]);

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
          panelData={panelData}
          apiError={apiError}
          justMergedClusterId={justMergedClusterId}
          onMergeClusters={handleMergeClusters}
          onSplitCluster={handleSplitCluster}
          onDetachLocation={handleDetachLocation}
          onRemoveCluster={handleRemoveCluster}
          onRemoveLocation={handleRemoveLocation}
          onUpdateClusterOffset={handleUpdateClusterOffset}
        />
      </div>

      <CalendarControl
        date={selectedAnalysisDate}
        onSelectDate={setSelectedAnalysisDate}
      />

      <BasemapToggle
        basemap={basemap}
        onChangeBasemap={setBasemap}
      />

      {/* WINDY-STYLE FLOATING LAYER DOCK */}
      <WindyLayerDock
        currentField={field}
        onChangeField={(newField) => setField(newField)}
        depthIndex={depthIndex}
        onChangeDepthIndex={setDepthIndex}
        onOpenMenu={() => setMenuOpen(true)}
      />

      {/* WINDY-STYLE SLIDE-OUT MENU DRAWER */}
      <WindyMenuDrawer
        isOpen={menuOpen}
        onClose={() => setMenuOpen(false)}
        basemap={basemap}
        onChangeBasemap={setBasemap}
        showGrid={showGrid}
        onToggleGrid={setShowGrid}
        showArgo={showArgo}
        onToggleArgo={setShowArgo}
        showSampling={showSampling}
        onToggleSampling={setShowSampling}
        status={status}
        analysisDate={selectedAnalysisDate}
      />

      {/* SLIM AUTHENTIC WINDY-STYLE COLOR SCALE / LEGEND */}
      <div className="legend" role="region" aria-label="Field Color Scale">
        <div className="ttl">
          <span>{selectedField.label}</span>
          <span style={{ color: "#FFAE1A", fontFamily: "var(--mono)", fontSize: "10.5px" }}>
            {selectedField.depth ? (depth === 0 ? "Surface" : `${depth}m`) : "2D Field"}
          </span>
        </div>
        <div className={`bar ${field}`}></div>
        <div className="scale">
          <span>Low</span>
          <span style={{ color: "#FFFFFF", fontWeight: 700 }}>{selectedField.unit}</span>
          <span>High</span>
        </div>
      </div>
    </>
  );
}
