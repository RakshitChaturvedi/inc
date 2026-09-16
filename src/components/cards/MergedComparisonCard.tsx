import React from "react";
import type { SelectedLocation } from "../../types/comparison";
import { ComparisonChart } from "../comparison/ComparisonChart";

interface MergedComparisonCardProps {
  locations: SelectedLocation[];
  date: string;
  fieldId: string;
  fieldLabel: string;
  fieldUnit: string;
  isDepthField?: boolean;
  activeDepth?: number;
  onClose: () => void;
  onSplitAll: () => void;
  onDetachLocation: (locId: string) => void;
  onRemoveLocation: (locId: string) => void;
  onPointerDownDrag: (e: React.PointerEvent) => void;
  isDraggingThis: boolean;
  isDropTarget: boolean;
  draggedLocationLabel?: string;
  justMerged?: boolean;
}

export function MergedComparisonCard({
  locations,
  date,
  fieldId,
  fieldLabel,
  fieldUnit,
  isDepthField = true,
  activeDepth,
  onClose,
  onSplitAll,
  onDetachLocation,
  onRemoveLocation,
  onPointerDownDrag,
  isDraggingThis,
  isDropTarget,
  draggedLocationLabel,
  justMerged,
}: MergedComparisonCardProps) {
  const [isZoomed, setIsZoomed] = React.useState(false);
  const [customWidth, setCustomWidth] = React.useState<number | null>(null);
  const resizeStart = React.useRef<{ startX: number; initialW: number } | null>(null);

  const handlePointerDownResize = (e: React.PointerEvent) => {
    e.stopPropagation();
    const currentW = customWidth ?? (isZoomed ? 680 : 440);
    resizeStart.current = { startX: e.clientX, initialW: currentW };
    try {
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const handlePointerMoveResize = (e: React.PointerEvent) => {
    if (!resizeStart.current) return;
    const dx = e.clientX - resizeStart.current.startX;
    const newW = Math.max(380, Math.min(920, resizeStart.current.initialW + dx));
    setCustomWidth(newW);
    setIsZoomed(newW > 540);
  };

  const handlePointerUpResize = (e: React.PointerEvent) => {
    resizeStart.current = null;
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const handleToggleZoom = () => {
    if (isZoomed) {
      setIsZoomed(false);
      setCustomWidth(null);
    } else {
      setIsZoomed(true);
      setCustomWidth(680);
    }
  };

  return (
    <div
      className={`merged-comparison-card ${isZoomed ? "is-zoomed" : ""} ${
        isDraggingThis ? "is-dragging" : ""
      } ${isDropTarget ? "is-drop-target" : ""} ${
        justMerged ? "merge-pulse" : ""
      }`}
      style={{ width: customWidth ? `${customWidth}px` : undefined }}
      onPointerDown={(e) => e.stopPropagation()}
      onWheel={(e) => e.stopPropagation()}
    >
      {/* Drop Target Merge Overlay Indicator */}
      {isDropTarget && (
        <div className="card-merge-overlay">
          <div className="card-merge-banner">
            <span className="merge-icon">⚡</span>
            <span>
              DROP TO ADD {draggedLocationLabel ? `[${draggedLocationLabel}]` : "LOCATION"} TO COMPARISON
            </span>
          </div>
        </div>
      )}

      {/* Draggable Header */}
      <div
        className="card-header comp-card-header"
        onPointerDown={onPointerDownDrag}
        title="Drag to reposition comparison window"
      >
        <div className="card-header-left">
          <div className="comp-badge-stack">
            {locations.map((loc) => (
              <span
                key={loc.id}
                className="card-badge"
                style={{ backgroundColor: loc.color }}
              >
                {loc.label}
              </span>
            ))}
          </div>
          <span className="card-title">
            COMPARE · {locations.length} LOCATIONS {isZoomed ? "(ZOOMED)" : ""}
          </span>
        </div>

        <div className="card-header-right">
          <button
            type="button"
            className={`comp-zoom-btn ${isZoomed ? "active" : ""}`}
            onClick={handleToggleZoom}
            onPointerDown={(e) => e.stopPropagation()}
            title={isZoomed ? "Reset zoom (100%)" : "Zoom in to see all depth points clearly"}
          >
            {isZoomed ? "RESET ZOOM" : "ZOOM +"}
          </button>
          <button
            type="button"
            className="comp-split-btn"
            onClick={onSplitAll}
            onPointerDown={(e) => e.stopPropagation()}
            title="Split comparison back into individual graphs"
          >
            SPLIT
          </button>
          <div className="card-drag-grip" title="Drag to move">
            <svg width="10" height="12" viewBox="0 0 10 12" fill="none">
              <circle cx="2" cy="2" r="1.2" fill="#99A8A9" />
              <circle cx="8" cy="2" r="1.2" fill="#99A8A9" />
              <circle cx="2" cy="6" r="1.2" fill="#99A8A9" />
              <circle cx="8" cy="6" r="1.2" fill="#99A8A9" />
              <circle cx="2" cy="10" r="1.2" fill="#99A8A9" />
              <circle cx="8" cy="10" r="1.2" fill="#99A8A9" />
            </svg>
          </div>
          <button
            type="button"
            className="card-close-btn"
            onClick={onClose}
            onPointerDown={(e) => e.stopPropagation()}
            title="Close comparison"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Chips bar with individual detach and remove controls */}
      <div className="card-chips-bar">
        {locations.map((loc) => (
          <div key={loc.id} className="card-chip-item">
            <span
              className="chip-badge"
              style={{ backgroundColor: loc.color }}
            >
              {loc.label}
            </span>
            <span className="chip-coord">
              {loc.coord.lat.toFixed(2)}°, {loc.coord.lon.toFixed(2)}°
            </span>
            <button
              type="button"
              className="chip-action-btn chip-detach-btn"
              onClick={() => onDetachLocation(loc.id)}
              onPointerDown={(e) => e.stopPropagation()}
              title={`Detach Location ${loc.label} into its own graph`}
            >
              Detach
            </button>
            <button
              type="button"
              className="chip-action-btn chip-remove-btn"
              onClick={() => onRemoveLocation(loc.id)}
              onPointerDown={(e) => e.stopPropagation()}
              title={`Remove Location ${loc.label}`}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Meta */}
      <div className="card-meta">
        <span className="card-date">{date}</span>
        <span className="comp-meta-desc">OceanEmbed prediction profiles</span>
      </div>

      {/* Chart Body */}
      <div className="card-body comp-chart-body">
        <div className="card-chart-header">
          <div className="card-chart-title">
            {fieldId === "uncertainty"
              ? "UNCERTAINTY COMPARISON (OVERALL COLUMN)"
              : isDepthField
              ? "DEPTH PROFILE COMPARISON"
              : "SURFACE PREDICTION COMPARISON"}
          </div>
          <div className="card-chart-field">{fieldLabel}</div>
          <div className="card-chart-unit">
            {fieldId === "uncertainty" ? "Overall Temperature (σ °C) & Salinity (σ psu)" : fieldUnit}
          </div>
        </div>

        {fieldId === "uncertainty" ? (
          <div className="card-merged-uncertainty-list">
            {locations.map((loc) => {
              const tempUncList = loc.profile?.depths
                ?.map((d) => d.oceanEmbed?.uncertainty)
                .filter((v): v is number => v !== undefined && v !== null && !isNaN(v)) ?? [];
              const meanTemp = tempUncList.length > 0
                ? tempUncList.reduce((a, b) => a + b, 0) / tempUncList.length
                : (loc.profile?.overallTempUncertainty ?? loc.profile?.confidence ?? 0.28);

              const salUncList = loc.profile?.depths
                ?.map((d) => d.oceanEmbed?.salinityUncertainty ?? (d.oceanEmbed?.uncertainty !== undefined ? d.oceanEmbed.uncertainty * 0.28 : undefined))
                .filter((v): v is number => v !== undefined && v !== null && !isNaN(v)) ?? [];
              const meanSal = salUncList.length > 0
                ? salUncList.reduce((a, b) => a + b, 0) / salUncList.length
                : (loc.profile?.overallSalUncertainty ?? meanTemp * 0.28);

              const dMatch = loc.profile?.depths?.find(
                (d) => activeDepth !== undefined && Math.abs(d.depth - activeDepth) < 1e-3
              );
              const depthTemp = dMatch?.oceanEmbed?.uncertainty;
              const depthSal = dMatch?.oceanEmbed?.salinityUncertainty;

              return (
                <div key={loc.id} className="card-merged-unc-row" style={{ borderLeft: `3px solid ${loc.color}` }}>
                  <div className="merged-unc-left">
                    <div className="merged-unc-id-row">
                      <span className="card-badge" style={{ backgroundColor: loc.color }}>
                        {loc.label}
                      </span>
                      <span className="merged-unc-coord">
                        {loc.coord.lat.toFixed(2)}°N, {loc.coord.lon.toFixed(2)}°E
                      </span>
                    </div>
                    {activeDepth !== undefined && depthTemp !== undefined && (
                      <div className="merged-unc-sub">
                        At {activeDepth}m: ±{depthTemp.toFixed(3)} °C · ±{(depthSal ?? depthTemp * 0.28).toFixed(3)} psu
                      </div>
                    )}
                  </div>

                  <div className="merged-unc-right">
                    <div className="merged-metric-item">
                      <div className="merged-metric-label">TEMP UNCERTAINTY</div>
                      <div className="merged-metric-val temp-accent">
                        ± {meanTemp.toFixed(3)} <span>σ °C</span>
                      </div>
                      <div className="merged-bar-track">
                        <div
                          className="merged-bar-fill temp-bar"
                          style={{ width: `${Math.min(100, Math.max(12, (meanTemp / 1.0) * 100))}%` }}
                        />
                      </div>
                    </div>

                    <div className="merged-metric-item">
                      <div className="merged-metric-label">SALINITY UNCERTAINTY</div>
                      <div className="merged-metric-val sal-accent">
                        ± {meanSal.toFixed(3)} <span>σ psu</span>
                      </div>
                      <div className="merged-bar-track">
                        <div
                          className="merged-bar-fill sal-bar"
                          style={{ width: `${Math.min(100, Math.max(12, (meanSal / 0.5) * 100))}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : isDepthField ? (
          <ComparisonChart
            locations={locations}
            variable={fieldId}
            fieldLabel={fieldLabel}
            fieldUnit={fieldUnit}
            isZoomed={isZoomed}
          />
        ) : (
          <div style={{ padding: "14px 10px", display: "flex", flexDirection: "column", gap: "10px" }}>
            {locations.map((loc) => {
              const val =
                fieldId === "tchp"
                  ? loc.profile?.tchp
                  : fieldId === "mld"
                  ? loc.profile?.mld
                  : fieldId === "d26"
                  ? loc.profile?.d26
                  : undefined;

              return (
                <div
                  key={loc.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "9px 12px",
                    background: "rgba(10, 17, 24, 0.75)",
                    border: "1px solid var(--border-neutral)",
                    borderLeft: `3px solid ${loc.color}`,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                    <span className="card-badge" style={{ backgroundColor: loc.color }}>
                      {loc.label}
                    </span>
                    <div>
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "#F5FAFA" }}>
                        {loc.coord.lat.toFixed(2)}°N, {loc.coord.lon.toFixed(2)}°E
                      </div>
                      <div style={{ fontSize: "10px", color: "#99A8A9" }}>
                        nearest ARGO {loc.profile?.nearestArgoKm ?? 42} km
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "16px", fontWeight: 700, color: "#F5FAFA", fontFamily: "var(--mono, monospace)" }}>
                      {val !== undefined ? val.toFixed(2) : "—"} <span style={{ fontSize: "10px", color: "#99A8A9" }}>{fieldUnit}</span>
                    </div>
                    {fieldId === "tchp" && loc.profile?.d26 !== undefined && (
                      <div style={{ fontSize: "9px", color: "#99A8A9" }}>
                        D26: {loc.profile.d26.toFixed(1)} m
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Manual Drag Resize Corner Grip */}
      <div
        className="card-resize-corner"
        onPointerDown={handlePointerDownResize}
        onPointerMove={handlePointerMoveResize}
        onPointerUp={handlePointerUpResize}
        onPointerCancel={handlePointerUpResize}
        title="Drag corner to manually resize / zoom graph"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <line x1="9" y1="3" x2="3" y2="9" stroke="#99A8A9" strokeWidth="1.2" />
          <line x1="9" y1="6" x2="6" y2="9" stroke="#99A8A9" strokeWidth="1.2" />
        </svg>
      </div>
    </div>
  );
}
