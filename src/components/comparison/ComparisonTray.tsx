import React, { useRef } from "react";
import type { SelectedLocation } from "../../types/comparison";

interface ComparisonTrayProps {
  locations: SelectedLocation[];
  onRemoveLocation: (id: string) => void;
  onCompare: () => void;
  isDragOver: boolean;
  onClearAll: () => void;
}

export function ComparisonTray({
  locations,
  onRemoveLocation,
  onCompare,
  isDragOver,
  onClearAll,
}: ComparisonTrayProps) {
  const trayRef = useRef<HTMLDivElement>(null);

  if (locations.length < 2) return null;

  return (
    <div
      ref={trayRef}
      className={`comparison-tray ${isDragOver ? "drag-over" : ""}`}
      id="comparison-tray"
    >
      <div className="comp-tray-header">
        <div className="comp-tray-title">
          COMPARE LOCATIONS ({locations.length})
        </div>
        <button
          type="button"
          className="comp-tray-clear-btn"
          onClick={onClearAll}
          title="Clear all selections"
        >
          CLEAR
        </button>
      </div>

      {/* Locations List */}
      <div className="comp-tray-list">
        {locations.map((loc) => (
          <div key={loc.id} className="comp-tray-item">
            <span
              className="comp-tray-badge"
              style={{ borderColor: loc.color, color: loc.color }}
            >
              {loc.label}
            </span>
            <span className="comp-tray-coord">
              {loc.coord.lat.toFixed(2)}°N, {loc.coord.lon.toFixed(2)}°E
            </span>
            <button
              type="button"
              className="comp-tray-remove-btn"
              onClick={() => onRemoveLocation(loc.id)}
              aria-label={`Remove location ${loc.label}`}
              title="Remove location"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Drop Zone hint / status */}
      <div className={`comp-tray-dropzone ${isDragOver ? "active" : ""}`}>
        {isDragOver ? "DROP LOCATION TO COMPARE" : "DRAG LOCATIONS HERE TO COMPARE"}
      </div>

      {/* Actions */}
      <button
        type="button"
        className="comp-tray-btn"
        onClick={onCompare}
      >
        COMPARE SELECTED ({locations.length})
      </button>
    </div>
  );
}
