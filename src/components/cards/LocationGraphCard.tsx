import React from "react";
import type { SelectedLocation } from "../../types/comparison";
import { DepthChart } from "../popup/DepthChart";
import { geoService } from "../../services/GeospatialService";

interface LocationGraphCardProps {
  location: SelectedLocation;
  date: string;
  fieldId: string;
  fieldLabel: string;
  fieldUnit: string;
  isDepthField: boolean;
  panelData?: any;
  apiError: string | null;
  onClose: () => void;
  onPointerDownDrag: (e: React.PointerEvent) => void;
  isDraggingThis: boolean;
  isDropTarget: boolean;
  draggedLocationLabel?: string;
  justMerged?: boolean;
}

export function LocationGraphCard({
  location,
  date,
  fieldId,
  fieldLabel,
  fieldUnit,
  isDepthField,
  panelData,
  apiError,
  onClose,
  onPointerDownDrag,
  isDraggingThis,
  isDropTarget,
  draggedLocationLabel,
  justMerged,
}: LocationGraphCardProps) {
  const coord = location.coord;
  const isLand = geoService.isLand(coord.lat, coord.lon);
  const isInDomain = geoService.isInDomain(coord.lat, coord.lon);

  return (
    <div
      className={`location-graph-card ${isDraggingThis ? "is-dragging" : ""} ${
        isDropTarget && !isLand ? "is-drop-target" : ""
      } ${justMerged ? "merge-pulse" : ""} ${isLand ? "is-land-card" : ""}`}
      onPointerDown={(e) => e.stopPropagation()}
      onWheel={(e) => e.stopPropagation()}
    >
      {/* Drop Target Merge Overlay Indicator (Only for valid ocean points) */}
      {isDropTarget && !isLand && (
        <div className="card-merge-overlay">
          <div className="card-merge-banner">
            <span className="merge-icon">⚡</span>
            <span>
              DROP TO MERGE {draggedLocationLabel ? `[${draggedLocationLabel}] + [${location.label}]` : `WITH [${location.label}]`}
            </span>
          </div>
        </div>
      )}

      {/* Draggable Card Header (disabled for land) */}
      <div
        className={`card-header ${isLand ? "land-locked-header" : ""}`}
        onPointerDown={isLand ? undefined : onPointerDownDrag}
        title={isLand ? "Land location (cannot be compared)" : "Drag onto another graph to compare"}
        style={isLand ? { cursor: "default" } : undefined}
      >
        <div className="card-header-left">
          <span
            className="card-badge"
            style={{ backgroundColor: location.color }}
          >
            {location.label}
          </span>
          <span className="card-title">
            {isLand ? "LAND" : "OCEAN"} · {coord.lat.toFixed(2)}°N, {coord.lon.toFixed(2)}°E
          </span>
        </div>

        <div className="card-header-right">
          {!isLand && (
            <div className="card-drag-grip" title="Drag to move or compare">
              <svg width="10" height="12" viewBox="0 0 10 12" fill="none">
                <circle cx="2" cy="2" r="1.2" fill="#99A8A9" />
                <circle cx="8" cy="2" r="1.2" fill="#99A8A9" />
                <circle cx="2" cy="6" r="1.2" fill="#99A8A9" />
                <circle cx="8" cy="6" r="1.2" fill="#99A8A9" />
                <circle cx="2" cy="10" r="1.2" fill="#99A8A9" />
                <circle cx="8" cy="10" r="1.2" fill="#99A8A9" />
              </svg>
            </div>
          )}
          <button
            type="button"
            className="card-close-btn"
            onClick={onClose}
            onPointerDown={(e) => e.stopPropagation()}
            title="Remove location"
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

      {/* Metadata Bar */}
      <div className="card-meta">
        <span className="card-date">{date}</span>
        {location.profile?.nearestArgoKm !== undefined && (
          <span className="card-argo">
            nearest ARGO {location.profile.nearestArgoKm.toFixed(0)} km
          </span>
        )}
      </div>

      {/* Card Content Body */}
      <div className="card-body">
        {isLand ? (
          <div className="card-message card-error">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ marginBottom: 6, stroke: "#99A8A9" }}
            >
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            <strong>LAND SELECTED</strong>
            <span>Prediction models strictly exclude terrestrial zones.</span>
          </div>
        ) : !isInDomain ? (
          <div className="card-message card-error">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ marginBottom: 6, stroke: "#99A8A9" }}
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            <strong>OUTSIDE DOMAIN</strong>
            <span>Active Domain: 5°N–30°N, 45°E–105°E</span>
          </div>
        ) : apiError ? (
          <div className="card-message card-error">
            <strong>PREDICTION UNAVAILABLE</strong>
            <span style={{ color: "#FF5C63" }}>{apiError}</span>
          </div>
        ) : location.loading || !location.profile ? (
          <div className="card-message card-loading">
            <div className="card-spinner" />
            <span>PREDICTING...</span>
          </div>
        ) : isDepthField && fieldId !== "uncertainty" && location.profile ? (
          <>
            <div className="card-chart-header">
              <div className="card-chart-title">DEPTH PROFILE</div>
              <div className="card-chart-field">{fieldLabel}</div>
              <div className="card-chart-unit">{fieldUnit}</div>
            </div>

            <DepthChart
              profile={location.profile}
              variable={fieldId}
              fieldLabel={fieldLabel}
              fieldUnit={fieldUnit}
            />

            <div className="card-chart-legend">
              <div
                className="card-legend-circle"
                style={{ background: location.color }}
              />
              <span>OceanEmbed prediction</span>
            </div>
          </>
        ) : fieldId === "uncertainty" && panelData ? (
          <div className="card-scalar-card">
            <div className="card-chart-title">UNCERTAINTY ESTIMATES</div>
            <div className="card-chart-field">{panelData.depth}m DEPTH</div>
            <div style={{ display: "flex", gap: "20px", marginTop: "12px" }}>
              <div>
                <div style={{ fontSize: "9px", color: "#99A8A9", fontWeight: 600 }}>
                  TEMPERATURE
                </div>
                <div className="card-scalar-val">
                  ± {panelData.tempUncertainty?.toFixed(3)} <span>σ °C</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: "9px", color: "#99A8A9", fontWeight: 600 }}>
                  SALINITY
                </div>
                <div className="card-scalar-val">
                  ± {panelData.salUncertainty?.toFixed(3)} <span>σ psu</span>
                </div>
              </div>
            </div>
          </div>
        ) : !isDepthField && panelData ? (
          <div className="card-scalar-card">
            <div className="card-chart-title">SURFACE PREDICTION</div>
            <div className="card-chart-field">{fieldLabel}</div>
            <div className="card-scalar-val">
              {panelData.value?.toFixed(2)} <span>{fieldUnit}</span>
            </div>
          </div>
        ) : (
          <div className="card-message card-error">PREDICTION UNAVAILABLE</div>
        )}
      </div>
    </div>
  );
}
