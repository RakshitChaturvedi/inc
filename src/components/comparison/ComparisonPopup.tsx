import React, { useState, useEffect, useRef } from "react";
import type { Map } from "maplibre-gl";
import type { SelectedLocation } from "../../types/comparison";
import { ComparisonChart } from "./ComparisonChart";

interface ComparisonPopupProps {
  map: Map | null;
  locations: SelectedLocation[];
  date: string;
  fieldId: string;
  fieldLabel: string;
  fieldUnit: string;
  onClose: () => void;
  onRemoveLocation: (id: string) => void;
  uncomparedLocations: SelectedLocation[];
  onAddLocationToComparison: (id: string) => void;
}

export function ComparisonPopup({
  map,
  locations,
  date,
  fieldId,
  fieldLabel,
  fieldUnit,
  onClose,
  onRemoveLocation,
  uncomparedLocations,
  onAddLocationToComparison,
}: ComparisonPopupProps) {
  const popupRef = useRef<HTMLDivElement>(null);

  // Dragging popup state
  const [offset, setOffset] = useState({ x: 50, y: 80 });
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, offsetX: 0, offsetY: 0 });

  // Escape key closes comparison
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Projected screen positions of compared locations for dynamic SVG connector lines
  const [projectedOrigins, setProjectedOrigins] = useState<
    Array<{ id: string; x: number; y: number; color: string }>
  >([]);

  useEffect(() => {
    if (!map) return;

    const updateProjectedPositions = () => {
      const positions = locations.map((loc) => {
        const p = map.project([loc.coord.lon, loc.coord.lat]);
        return { id: loc.id, x: p.x, y: p.y, color: loc.color };
      });
      setProjectedOrigins(positions);
    };

    updateProjectedPositions();
    map.on("move", updateProjectedPositions);
    map.on("zoom", updateProjectedPositions);
    map.on("resize", updateProjectedPositions);

    return () => {
      map.off("move", updateProjectedPositions);
      map.off("zoom", updateProjectedPositions);
      map.off("resize", updateProjectedPositions);
    };
  }, [map, locations]);

  // Initial positioning: top-right area
  useEffect(() => {
    const w = window.innerWidth;
    const popupWidth = Math.min(480, w - 40);
    setOffset({
      x: Math.max(20, w - popupWidth - 40),
      y: 70,
    });
  }, []);

  const handlePointerDown = (e: React.PointerEvent) => {
    isDragging.current = true;
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      offsetX: offset.x,
      offsetY: offset.y,
    };
    try {
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setOffset({
      x: Math.max(10, dragStart.current.offsetX + dx),
      y: Math.max(10, dragStart.current.offsetY + dy),
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    isDragging.current = false;
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const popupX = offset.x;
  const popupY = offset.y;
  // Anchor target on the popup for the connector lines: top-left corner
  const targetX = popupX;
  const targetY = popupY + 32;

  return (
    <>
      {/* Dynamic SVG Connector Lines Layer */}
      <svg
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 20,
        }}
      >
        {projectedOrigins.map((orig, i) => (
          <g key={`conn-${orig.id}`}>
            <line
              x1={orig.x}
              y1={orig.y}
              x2={targetX}
              y2={targetY + i * 4}
              stroke="#2B5AAF"
              strokeWidth="1.2"
              strokeDasharray="2 2"
              opacity={0.85}
            />
            <circle cx={orig.x} cy={orig.y} r="3" fill="#2B5AAF" />
          </g>
        ))}
      </svg>

      {/* Comparison Window */}
      <div
        ref={popupRef}
        className="comparison-popup"
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translate(${popupX}px, ${popupY}px)`,
          zIndex: 25,
        }}
        onPointerDown={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
      >
        {/* Drag Handle Header */}
        <div
          className="comp-header"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <div className="comp-header-info">
            <span className="comp-title">
              COMPARE · {locations.length} LOCATIONS
            </span>
            <span className="comp-date">{date}</span>
          </div>

          <div
            className="comp-close-btn"
            onClick={onClose}
            onPointerDown={(e) => e.stopPropagation()}
            title="Close comparison (ESC)"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </div>
        </div>

        {/* Location Chips Strip with individual remove buttons */}
        <div className="comp-chips-strip">
          {locations.map((loc) => (
            <div key={loc.id} className="comp-strip-chip">
              <span
                className="comp-strip-badge"
                style={{ background: loc.color }}
              >
                {loc.label}
              </span>
              <span className="comp-strip-coord">
                {loc.coord.lat.toFixed(2)}°N, {loc.coord.lon.toFixed(2)}°E
              </span>
              <button
                type="button"
                className="comp-strip-remove"
                onClick={() => onRemoveLocation(loc.id)}
                title={`Remove Location ${loc.label}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>

        {/* Notice to add any newly selected map locations */}
        {uncomparedLocations.length > 0 && (
          <div className="comp-uncompared-banner">
            <span className="comp-uncompared-text">
              Selected on map:{" "}
              {uncomparedLocations.map((l) => l.label).join(", ")}
            </span>
            {uncomparedLocations.map((l) => (
              <button
                key={l.id}
                type="button"
                className="comp-add-btn"
                onClick={() => onAddLocationToComparison(l.id)}
              >
                + ADD {l.label}
              </button>
            ))}
          </div>
        )}

        {/* Body containing single shared depth profile chart */}
        <div className="comp-body">
          <div className="comp-chart-meta">
            <span className="comp-variable-label">{fieldLabel}</span>
            <span className="comp-variable-desc">OceanEmbed prediction profiles</span>
          </div>

          <ComparisonChart
            locations={locations}
            variable={fieldId}
            fieldLabel={fieldLabel}
            fieldUnit={fieldUnit}
          />
        </div>
      </div>
    </>
  );
}
