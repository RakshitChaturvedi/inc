import React, { useRef, useCallback, useState } from "react";
import { DEPTHS } from "../../api/types";

interface DepthControlProps {
  depthIndex: number;
  onChangeDepthIndex: (newIndex: number) => void;
  isDepthField: boolean;
  fieldLabel: string;
}

// Depth milestones to prominently show text labels for
const MILESTONE_DEPTHS = new Set([0, 20, 50, 100, 200, 500, 1000]);

function getDepthZoneName(d: number): string {
  if (d === 0) return "Surface Layer";
  if (d <= 50) return "Mixed Layer";
  if (d <= 200) return "Thermocline";
  if (d <= 500) return "Mesopelagic";
  return "Deep Ocean";
}

export const DepthControl: React.FC<DepthControlProps> = ({
  depthIndex,
  onChangeDepthIndex,
  isDepthField,
  fieldLabel,
}) => {
  const currentDepth = DEPTHS[depthIndex];
  const trackRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // Step shallower (smaller depth value = lower index)
  const handleStepUp = useCallback(() => {
    if (!isDepthField) return;
    if (depthIndex > 0) {
      onChangeDepthIndex(depthIndex - 1);
    }
  }, [depthIndex, isDepthField, onChangeDepthIndex]);

  // Step deeper (larger depth value = higher index)
  const handleStepDown = useCallback(() => {
    if (!isDepthField) return;
    if (depthIndex < DEPTHS.length - 1) {
      onChangeDepthIndex(depthIndex + 1);
    }
  }, [depthIndex, isDepthField, onChangeDepthIndex]);

  // Handle click / drag position conversion to nearest depth index
  const updateFromPointerPosition = useCallback(
    (clientY: number) => {
      if (!trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const relativeY = Math.max(0, Math.min(rect.height, clientY - rect.top));
      const ratio = relativeY / rect.height;
      const targetIndex = Math.round(ratio * (DEPTHS.length - 1));
      const clampedIndex = Math.max(0, Math.min(DEPTHS.length - 1, targetIndex));
      onChangeDepthIndex(clampedIndex);
    },
    [onChangeDepthIndex]
  );

  const handlePointerDown = (e: React.PointerEvent) => {
    if (!isDepthField) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    setIsDragging(true);
    updateFromPointerPosition(e.clientY);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (isDragging) {
      updateFromPointerPosition(e.clientY);
    } else if (trackRef.current) {
      const rect = trackRef.current.getBoundingClientRect();
      const relativeY = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
      const ratio = relativeY / rect.height;
      const nearestIdx = Math.round(ratio * (DEPTHS.length - 1));
      setHoverIndex(nearestIdx);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isDragging) {
      setIsDragging(false);
      (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
    }
  };

  // Mouse wheel scroll to smoothly step depth
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (!isDepthField) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.deltaY < 0) {
        handleStepUp();
      } else if (e.deltaY > 0) {
        handleStepDown();
      }
    },
    [isDepthField, handleStepUp, handleStepDown]
  );

  // Position ratio (0 to 1) for the active handle
  const activeRatio = depthIndex / (DEPTHS.length - 1);
  const activePercent = activeRatio * 100;

  if (!isDepthField) {
    return (
      <aside
        className="depth-control-panel depth-2d-muted"
        aria-label="Depth control unavailable for 2D field"
      >
        <div className="depth-2d-pill">
          <span className="depth-2d-dot"></span>
          <span className="depth-2d-title">SURFACE ONLY</span>
          <span className="depth-2d-sub">{fieldLabel} (2D)</span>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className={`depth-control-panel ${isDragging ? "dragging" : ""}`}
      onWheel={handleWheel}
      aria-label="Ocean depth selector"
      role="region"
    >
      {/* Top Header with Stepper Up */}
      <div className="depth-panel-header">
        <div className="depth-header-title">
          <span className="depth-pulse-dot"></span>
          <span>DEPTH</span>
        </div>
        <button
          type="button"
          className="depth-step-btn"
          onClick={handleStepUp}
          disabled={depthIndex <= 0}
          title="Step shallower (▲)"
          aria-label="Step shallower"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="18 15 12 9 6 15" />
          </svg>
        </button>
      </div>

      {/* Interactive Track Area */}
      <div
        ref={trackRef}
        className="depth-track-container"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={() => setHoverIndex(null)}
      >
        {/* Track groove */}
        <div className="depth-rail-groove">
          <div
            className="depth-rail-fill"
            style={{ height: `${activePercent}%` }}
          />
        </div>

        {/* Ticks and Milestone Labels */}
        {DEPTHS.map((d, idx) => {
          const tickPercent = (idx / (DEPTHS.length - 1)) * 100;
          const isMilestone = MILESTONE_DEPTHS.has(d);
          const isSelected = idx === depthIndex;
          const isHovered = idx === hoverIndex && !isSelected;

          return (
            <div
              key={d}
              className={`depth-station ${isMilestone ? "milestone" : "minor"} ${isSelected ? "selected" : ""} ${isHovered ? "hovered" : ""}`}
              style={{ top: `${tickPercent}%` }}
              onClick={(e) => {
                e.stopPropagation();
                onChangeDepthIndex(idx);
              }}
              title={`${d}m (${getDepthZoneName(d)})`}
            >
              <div className="depth-station-pip" />
              {isMilestone && (
                <span className="depth-station-label">
                  {d === 0 ? "0m" : `${d}m`}
                </span>
              )}
            </div>
          );
        })}

        {/* Glowing Interactive Handle */}
        <div
          className="depth-slider-handle"
          style={{ top: `${activePercent}%` }}
        >
          <div className="handle-ring" />
          <div className="handle-center-dot" />
          <div className="handle-floating-callout">
            {currentDepth === 0 ? "0m" : `${currentDepth}m`}
          </div>
        </div>
      </div>

      {/* Bottom Footer with Stepper Down & Metric Readout */}
      <div className="depth-panel-footer">
        <button
          type="button"
          className="depth-step-btn"
          onClick={handleStepDown}
          disabled={depthIndex >= DEPTHS.length - 1}
          title="Step deeper (▼)"
          aria-label="Step deeper"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {/* Active Depth Readout Box */}
        <div className="depth-active-readout">
          <div className="readout-val">
            {currentDepth === 0 ? "SURFACE" : `${currentDepth}m`}
          </div>
          <div className="readout-zone">{getDepthZoneName(currentDepth)}</div>
        </div>
      </div>
    </aside>
  );
};
