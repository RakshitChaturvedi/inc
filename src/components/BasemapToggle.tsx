import React from "react";
import type { BasemapId } from "../map/basemaps";

interface BasemapToggleProps {
  basemap: BasemapId;
  onChangeBasemap: (basemap: BasemapId) => void;
}

export const BasemapToggle: React.FC<BasemapToggleProps> = ({
  basemap,
  onChangeBasemap,
}) => {
  return (
    <div className="floating-basemap-toggle" role="group" aria-label="Map Basemap Switcher">
      <button
        type="button"
        className={`basemap-segment-btn ${basemap === "basic" ? "active" : ""}`}
        onClick={() => onChangeBasemap("basic")}
        aria-pressed={basemap === "basic"}
      >
        <svg
          className="basemap-icon"
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
          <line x1="8" y1="2" x2="8" y2="18" />
          <line x1="16" y1="6" x2="16" y2="22" />
        </svg>
        <span className="basemap-label">MAP</span>
      </button>

      <button
        type="button"
        className={`basemap-segment-btn ${basemap === "satellite" ? "active" : ""}`}
        onClick={() => onChangeBasemap("satellite")}
        aria-pressed={basemap === "satellite"}
      >
        <svg
          className="basemap-icon"
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
          <path d="M2 12h20" />
        </svg>
        <span className="basemap-label">SAT</span>
      </button>
    </div>
  );
};
