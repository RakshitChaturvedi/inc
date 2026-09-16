import React, { useRef } from "react";
import type { SelectedLocation } from "../../types/comparison";

interface ComparisonTargetProps {
  locations: SelectedLocation[];
  droppedLocationIds: Set<string>;
  onRemoveLocation: (id: string) => void;
  onClearAll: () => void;
  isDragOver: boolean;
  onDirectCompare: () => void;
  justDroppedId: string | null;
  isComparing: boolean;
}

export function ComparisonTarget({
  locations,
  droppedLocationIds,
  onRemoveLocation,
  onClearAll,
  isDragOver,
  onDirectCompare,
  justDroppedId,
  isComparing,
}: ComparisonTargetProps) {
  const targetRef = useRef<HTMLDivElement>(null);

  if (locations.length < 2) return null;

  const droppedCount = locations.filter((loc) => droppedLocationIds.has(loc.id)).length;

  return (
    <div
      ref={targetRef}
      id="comparison-target"
      className={`comparison-target-dock ${isDragOver ? "target-active" : ""} ${justDroppedId ? "target-confirm" : ""}`}
      onClick={onDirectCompare}
      role="button"
      tabIndex={0}
      title="Drop locations here or click to compare"
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onDirectCompare();
        }
      }}
    >
      {/* Target Action Icon & Prompt */}
      <div className="target-core-zone">
        <div className="target-icon-wrap">
          <svg
            className="target-down-arrow"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <polyline points="19 12 12 19 5 12" />
          </svg>
        </div>

        <div className="target-label-group">
          <span className="target-action-text">
            {isDragOver
              ? "ADD LOCATION ↓"
              : justDroppedId
              ? "LOCATION DROPPED"
              : isComparing
              ? "DROP TO ADD TO COMPARISON"
              : "DROP TO COMPARE"}
          </span>
          <span className="target-sub-text">
            {isComparing
              ? `Comparing ${droppedCount} of ${locations.length} locations`
              : `${droppedCount} of ${locations.length} locations ready`}
          </span>
        </div>
      </div>

      {/* Selected Location Chips Strip with Status & Remove Actions */}
      <div className="target-chips-row" onClick={(e) => e.stopPropagation()}>
        {locations.map((loc) => {
          const isDropped = droppedLocationIds.has(loc.id);
          const isFreshDrop = justDroppedId === loc.id;

          return (
            <div
              key={loc.id}
              className={`target-location-chip ${isDropped ? "dropped" : "pending"} ${isFreshDrop ? "fresh-drop" : ""}`}
              style={{
                borderColor: isDropped ? loc.color : "rgba(153, 168, 169, 0.3)",
              }}
            >
              <span
                className="target-chip-badge"
                style={{
                  background: isDropped ? loc.color : "transparent",
                  color: isDropped ? "#0A1118" : loc.color,
                  borderColor: loc.color,
                }}
              >
                {loc.label}
              </span>
              <span className="target-chip-coord">
                {loc.coord.lat.toFixed(1)}°, {loc.coord.lon.toFixed(1)}°
              </span>
              <button
                type="button"
                className="target-chip-remove"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveLocation(loc.id);
                }}
                aria-label={`Remove location ${loc.label}`}
                title={`Remove Location ${loc.label}`}
              >
                ×
              </button>
            </div>
          );
        })}

        <button
          type="button"
          className="target-clear-all"
          onClick={(e) => {
            e.stopPropagation();
            onClearAll();
          }}
          title="Clear all selected locations"
        >
          CLEAR
        </button>
      </div>
    </div>
  );
}
