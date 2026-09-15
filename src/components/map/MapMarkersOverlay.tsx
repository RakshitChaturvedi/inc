import React, { useEffect, useState, useRef } from "react";
import type { Map } from "maplibre-gl";
import type { SelectedLocation } from "../../types/comparison";

interface MapMarkersOverlayProps {
  map: Map | null;
  locations: SelectedLocation[];
  onToggleLocation: (loc: SelectedLocation) => void;
  onDragLocationStart?: (loc: SelectedLocation, startPos: { x: number; y: number }) => void;
  onDragLocationMove?: (currentPos: { x: number; y: number }) => void;
  onDragLocationEnd?: (loc: SelectedLocation, endPos: { x: number; y: number }) => void;
  activeDragLocation?: SelectedLocation | null;
  dragPointerPos?: { x: number; y: number } | null;
}

export function MapMarkersOverlay({
  map,
  locations,
  onToggleLocation,
  onDragLocationStart,
  onDragLocationMove,
  onDragLocationEnd,
  activeDragLocation,
  dragPointerPos,
}: MapMarkersOverlayProps) {
  const [, setTick] = useState(0);
  const dragInfo = useRef<{
    loc: SelectedLocation;
    startX: number;
    startY: number;
    hasMoved: boolean;
  } | null>(null);

  useEffect(() => {
    if (!map) return;
    const handleUpdate = () => setTick((t) => t + 1);
    map.on("move", handleUpdate);
    map.on("zoom", handleUpdate);
    map.on("resize", handleUpdate);
    return () => {
      map.off("move", handleUpdate);
      map.off("zoom", handleUpdate);
      map.off("resize", handleUpdate);
    };
  }, [map]);

  const handlePointerDown = (loc: SelectedLocation, e: React.PointerEvent) => {
    e.stopPropagation();
    dragInfo.current = {
      loc,
      startX: e.clientX,
      startY: e.clientY,
      hasMoved: false,
    };
    try {
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragInfo.current) return;
    const dx = e.clientX - dragInfo.current.startX;
    const dy = e.clientY - dragInfo.current.startY;
    if (!dragInfo.current.hasMoved && Math.hypot(dx, dy) > 4) {
      dragInfo.current.hasMoved = true;
      onDragLocationStart?.(dragInfo.current.loc, { x: e.clientX, y: e.clientY });
    }
    if (dragInfo.current.hasMoved) {
      onDragLocationMove?.({ x: e.clientX, y: e.clientY });
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!dragInfo.current) return;
    const { loc, hasMoved } = dragInfo.current;
    if (hasMoved) {
      onDragLocationEnd?.(loc, { x: e.clientX, y: e.clientY });
    } else {
      // Direct click on marker = toggle / remove
      onToggleLocation(loc);
    }
    dragInfo.current = null;
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  if (!map) return null;

  // Active dragging line origin
  let dragOrigin: { x: number; y: number } | null = null;
  if (activeDragLocation) {
    const p = map.project([activeDragLocation.coord.lon, activeDragLocation.coord.lat]);
    dragOrigin = { x: p.x, y: p.y };
  }

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 15,
        overflow: "hidden",
      }}
    >
      {/* SVG layer for drag connectors */}
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
        {dragOrigin && dragPointerPos && (
          <>
            <line
              x1={dragOrigin.x}
              y1={dragOrigin.y}
              x2={dragPointerPos.x}
              y2={dragPointerPos.y}
              stroke="#2B5AAF"
              strokeWidth="1.2"
              strokeDasharray="3 3"
            />
            <circle cx={dragOrigin.x} cy={dragOrigin.y} r="3.5" fill="#2B5AAF" />
          </>
        )}
      </svg>

      {/* Render each location marker */}
      {locations.map((loc) => {
        const point = map.project([loc.coord.lon, loc.coord.lat]);
        const isDraggingThis = activeDragLocation?.id === loc.id;

        return (
          <div
            key={loc.id}
            style={{
              position: "absolute",
              left: `${point.x}px`,
              top: `${point.y}px`,
              transform: "translate(-50%, -50%)",
              pointerEvents: "auto",
              cursor: isDraggingThis ? "grabbing" : "grab",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              opacity: isDraggingThis ? 0.6 : 1,
              userSelect: "none",
            }}
            onPointerDown={(e) => handlePointerDown(loc, e)}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
            title={`Location ${loc.label} (${loc.coord.lat.toFixed(2)}°N, ${loc.coord.lon.toFixed(2)}°E) - Drag to compare target`}
          >
            {/* Single Whole Point Badge */}
            <div
              style={{
                width: "22px",
                height: "22px",
                borderRadius: "50%",
                background: "#0A1118",
                border: `2px solid ${loc.color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: isDraggingThis
                  ? `0 0 0 3px ${loc.color}, 0 4px 12px rgba(0,0,0,0.85)`
                  : "0 2px 8px rgba(0,0,0,0.75), 0 0 0 1px rgba(0,0,0,0.5)",
                color: "#FFFFFF",
                fontSize: "11px",
                fontWeight: 700,
                fontFamily: "var(--sans)",
                lineHeight: 1,
                flexShrink: 0,
                transition: "transform 0.15s, box-shadow 0.15s",
                transform: isDraggingThis ? "scale(1.15)" : "scale(1)",
              }}
            >
              {loc.label}
            </div>
          </div>
        );
      })}

      {/* Floating Drag Avatar following pointer */}
      {activeDragLocation && dragPointerPos && (
        <div
          style={{
            position: "absolute",
            left: `${dragPointerPos.x}px`,
            top: `${dragPointerPos.y}px`,
            transform: "translate(10px, 10px)",
            pointerEvents: "none",
            background: "#0A1118",
            border: "1px solid #2B5AAF",
            color: "#ADBCC7",
            padding: "3px 7px",
            fontSize: "10.5px",
            fontWeight: 500,
            borderRadius: "0px",
            display: "flex",
            alignItems: "center",
            gap: "5px",
            boxShadow: "0 6px 18px rgba(0,0,0,0.75)",
            zIndex: 100,
          }}
        >
          <span style={{ color: activeDragLocation.color, fontWeight: 700 }}>
            {activeDragLocation.label}
          </span>
          <span style={{ color: "#99A8A9" }}>
            {activeDragLocation.coord.lat.toFixed(1)}°N, {activeDragLocation.coord.lon.toFixed(1)}°E
          </span>
        </div>
      )}
    </div>
  );
}
