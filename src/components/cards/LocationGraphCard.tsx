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
  activeDepth?: number;
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
  activeDepth,
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

  // Scalar prediction value resolution: prioritize location.profile (which holds tchp, mld, d26) with fallback to panelData
  const scalarValue =
    fieldId === "tchp"
      ? (location.profile?.tchp ?? panelData?.value)
      : fieldId === "mld"
      ? (location.profile?.mld ?? panelData?.value)
      : fieldId === "d26"
      ? (location.profile?.d26 ?? panelData?.value)
      : panelData?.value;

  const hasScalarValue = scalarValue !== undefined && scalarValue !== null && !isNaN(Number(scalarValue));

  // Uncertainty calculations (Overall Temperature Uncertainty and Overall Salinity Uncertainty)
  const tempUncertaintyList = location.profile?.depths
    ?.map((d) => d.oceanEmbed?.uncertainty)
    .filter((v): v is number => v !== undefined && v !== null && !isNaN(v)) ?? [];
  const overallTempUnc =
    tempUncertaintyList.length > 0
      ? tempUncertaintyList.reduce((a, b) => a + b, 0) / tempUncertaintyList.length
      : (location.profile?.overallTempUncertainty ?? panelData?.tempUncertainty ?? location.profile?.confidence ?? 0.28);

  const salUncertaintyList = location.profile?.depths
    ?.map((d) => d.oceanEmbed?.salinityUncertainty ?? (d.oceanEmbed?.uncertainty !== undefined ? d.oceanEmbed.uncertainty * 0.28 : undefined))
    .filter((v): v is number => v !== undefined && v !== null && !isNaN(v)) ?? [];
  const overallSalUnc =
    salUncertaintyList.length > 0
      ? salUncertaintyList.reduce((a, b) => a + b, 0) / salUncertaintyList.length
      : (location.profile?.overallSalUncertainty ?? panelData?.salUncertainty ?? overallTempUnc * 0.28);

  const depthMatch = location.profile?.depths?.find(
    (d) => activeDepth !== undefined && Math.abs(d.depth - activeDepth) < 1e-3
  );
  const activeDepthTempUnc = depthMatch?.oceanEmbed?.uncertainty ?? panelData?.tempUncertainty;
  const activeDepthSalUnc = depthMatch?.oceanEmbed?.salinityUncertainty ?? panelData?.salUncertainty;

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
        ) : location.loading ? (
          <div className="card-message card-loading">
            <div className="card-spinner" />
            <span>PREDICTING...</span>
          </div>
        ) : fieldId === "uncertainty" && (location.profile || panelData) ? (
          /* Dedicated Uncertainty Value View: Overall Temp & Overall Salinity Uncertainty */
          <div className="card-uncertainty-view">
            <div className="card-chart-header">
              <div className="card-chart-title">UNCERTAINTY ESTIMATES</div>
              <div className="card-chart-field">Prediction Confidence (σ)</div>
              <div className="card-chart-unit">0m – 1000m Water Column Aggregate</div>
            </div>

            <div className="card-uncertainty-blocks">
              {/* Overall Temperature Uncertainty */}
              <div className="card-unc-box unc-box-temp">
                <div className="unc-box-head">
                  <span className="unc-dot unc-dot-temp" />
                  <span className="unc-label">OVERALL TEMPERATURE UNCERTAINTY</span>
                </div>
                <div className="unc-value-row">
                  <span className="unc-val">± {overallTempUnc.toFixed(3)}</span>
                  <span className="unc-unit">σ °C</span>
                </div>
                <div className="unc-bar-track">
                  <div
                    className="unc-bar-fill unc-bar-temp"
                    style={{ width: `${Math.min(100, Math.max(12, (overallTempUnc / 1.0) * 100))}%` }}
                  />
                </div>
                <div className="unc-box-sub">Full Water Column Mean (0–1000m)</div>
              </div>

              {/* Overall Salinity Uncertainty */}
              <div className="card-unc-box unc-box-sal">
                <div className="unc-box-head">
                  <span className="unc-dot unc-dot-sal" />
                  <span className="unc-label">OVERALL SALINITY UNCERTAINTY</span>
                </div>
                <div className="unc-value-row">
                  <span className="unc-val">± {overallSalUnc.toFixed(3)}</span>
                  <span className="unc-unit">σ psu</span>
                </div>
                <div className="unc-bar-track">
                  <div
                    className="unc-bar-fill unc-bar-sal"
                    style={{ width: `${Math.min(100, Math.max(12, (overallSalUnc / 0.5) * 100))}%` }}
                  />
                </div>
                <div className="unc-box-sub">Full Water Column Mean (0–1000m)</div>
              </div>
            </div>

            {/* Selected Depth Slice Context */}
            {activeDepth !== undefined && (
              <div className="card-unc-depth-context">
                <div className="unc-depth-title">
                  <span>CURRENT DEPTH LAYER ({activeDepth}m)</span>
                </div>
                <div className="unc-depth-row">
                  <span>T: <strong>±{(activeDepthTempUnc ?? overallTempUnc).toFixed(3)} σ °C</strong></span>
                  <span className="unc-depth-sep">·</span>
                  <span>S: <strong>±{(activeDepthSalUnc ?? overallSalUnc).toFixed(3)} σ psu</strong></span>
                </div>
              </div>
            )}
          </div>
        ) : isDepthField && location.profile ? (
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
        ) : hasScalarValue ? (
          <div className="card-scalar-card">
            <div className="card-chart-title">SURFACE PREDICTION</div>
            <div className="card-chart-field">{fieldLabel}</div>
            <div className="card-scalar-val">
              {Number(scalarValue).toFixed(2)} <span>{fieldUnit}</span>
            </div>
            {fieldId === "tchp" && (location.profile?.d26 !== undefined || panelData?.d26 !== undefined) && (
              <div style={{ marginTop: "10px", fontSize: "11px", color: "#99A8A9" }}>
                26°C Isotherm Depth (D26): <strong style={{ color: "#F5FAFA" }}>{((location.profile?.d26 ?? panelData?.d26) as number).toFixed(1)} m</strong>
              </div>
            )}
            {(location.profile?.confidence !== undefined || panelData?.confidence !== undefined) && (
              <div style={{ marginTop: "6px", fontSize: "10px", color: "#99A8A9" }}>
                Confidence: ±{((location.profile?.confidence ?? panelData?.confidence) as number).toFixed(2)} σ
              </div>
            )}
          </div>
        ) : location.profile ? (
          /* Profile exists: show depth chart */
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
        ) : (
          <div className="card-message card-error">PREDICTION UNAVAILABLE</div>
        )}
      </div>
    </div>
  );
}
