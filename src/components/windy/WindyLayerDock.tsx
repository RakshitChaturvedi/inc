import React, { useState, useRef, useEffect } from "react";
import type { FieldId } from "../../api/types";
import { DEPTHS } from "../../api/types";

export interface FieldDefinition {
  id: FieldId;
  label: string;
  unit: string;
  depth: boolean;
  color: string;
  short: string;
  badgeClass: string;
}

export const WINDY_FIELDS: FieldDefinition[] = [
  {
    id: "temperature",
    label: "Temperature",
    unit: "°C",
    depth: true,
    color: "#FF9B5E",
    short: "OSTS",
    badgeClass: "badge-temperature",
  },
  {
    id: "salinity",
    label: "Salinity",
    unit: "psu",
    depth: true,
    color: "#58A6FF",
    short: "OSSS",
    badgeClass: "badge-salinity",
  },
  {
    id: "tchp",
    label: "Cyclone heat",
    unit: "kJ cm⁻²",
    depth: false,
    color: "#FF5C63",
    short: "TCHP",
    badgeClass: "badge-tchp",
  },
  {
    id: "mld",
    label: "Mixed layer",
    unit: "m",
    depth: false,
    color: "#A98BFF",
    short: "MLD",
    badgeClass: "badge-mld",
  },
  {
    id: "uncertainty",
    label: "Uncertainty",
    unit: "σ °C",
    depth: true,
    color: "#B8C4CC",
    short: "σ",
    badgeClass: "badge-uncertainty",
  },
];

interface WindyLayerDockProps {
  currentField: FieldId;
  onChangeField: (field: FieldId) => void;
  depthIndex: number;
  onChangeDepthIndex: (index: number) => void;
  onOpenMenu: () => void;
}

export const WindyLayerDock: React.FC<WindyLayerDockProps> = ({
  currentField,
  onChangeField,
  depthIndex,
  onChangeDepthIndex,
  onOpenMenu,
}) => {
  const [depthPickerOpen, setDepthPickerOpen] = useState(false);
  const depthFlyoutRef = useRef<HTMLDivElement>(null);

  const selectedFieldDef = WINDY_FIELDS.find((f) => f.id === currentField);
  const isDepthSupported = selectedFieldDef?.depth ?? false;
  const currentDepth = DEPTHS[depthIndex];

  // Close depth flyout on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        depthFlyoutRef.current &&
        !depthFlyoutRef.current.contains(event.target as Node)
      ) {
        setDepthPickerOpen(false);
      }
    }
    if (depthPickerOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [depthPickerOpen]);

  return (
    <aside className="windy-dock-container" role="toolbar" aria-label="Map Layer Selection">
      {/* 1. TOP MENU PILL (Red circular hamburger + Menu label) */}
      <div
        id="windy-menu-button"
        className="windy-menu-pill"
        onClick={onOpenMenu}
        role="button"
        tabIndex={0}
        title="Open OceanEmbed Console Menu"
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onOpenMenu();
          }
        }}
      >
        <span className="windy-menu-text">Menu</span>
        <div className="windy-menu-red-circle">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#FFFFFF"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="4" y1="7" x2="20" y2="7" />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="17" x2="20" y2="17" />
          </svg>
        </div>
      </div>

      {/* 2. LAYER PILLS STACK */}
      <div className="windy-layers-stack">
        {WINDY_FIELDS.map((item) => {
          const isActive = currentField === item.id;
          return (
            <div
              key={item.id}
              id={`windy-layer-${item.id}`}
              className={`windy-layer-row ${isActive ? "active" : ""}`}
              onClick={() => onChangeField(item.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onChangeField(item.id);
                }
              }}
              title={`${item.label} (${item.short})`}
            >
              {/* Authentic Frosted glass label pill on the left */}
              <div className="windy-label-pill">
                <span className="windy-layer-title">{item.label}</span>
              </div>

              {/* High-res circular preview badge on the right */}
              <div className={`windy-circle-badge ${item.badgeClass} ${isActive ? "active-ring" : ""}`}>
                {/* Authentic downward chevron on active item */}
                {isActive && (
                  <div className="windy-active-chevron" title="Active layer">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. OCEAN DEPTH SELECTOR (Windy Altitude Analogue) */}
      {isDepthSupported && (
        <div className="windy-depth-container" ref={depthFlyoutRef}>
          <div
            id="windy-depth-button"
            className={`windy-depth-row ${depthPickerOpen ? "expanded" : ""}`}
            onClick={() => setDepthPickerOpen(!depthPickerOpen)}
            role="button"
            tabIndex={0}
            title="Select ocean depth level"
          >
            <div className="windy-depth-pill">
              <span className="windy-depth-title">Depth</span>
              <span className="windy-depth-val">
                {currentDepth === 0 ? "Surface" : `${currentDepth}m`}
              </span>
            </div>

            {/* Circular Amber Depth Badge (Windy Altitude Analogue) */}
            <div className="windy-circle-badge windy-depth-badge">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="5" r="3" />
                <line x1="12" y1="22" x2="12" y2="8" />
                <path d="M5 12H2a10 10 0 0 0 20 0h-3" />
              </svg>
            </div>
          </div>

          {/* Vertical Depth Level Stepper Flyout (Opens to the left of the dock) */}
          {depthPickerOpen && (
            <div className="windy-depth-flyout">
              <div className="windy-depth-flyout-header">
                <span>VERTICAL LEVEL</span>
                <span className="windy-depth-unit">DEPTH (METERS)</span>
              </div>
              <div className="windy-depth-ladder">
                {DEPTHS.map((d, idx) => {
                  const isSelected = idx === depthIndex;
                  return (
                    <button
                      key={d}
                      type="button"
                      className={`windy-ladder-step ${isSelected ? "selected" : ""}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onChangeDepthIndex(idx);
                        setDepthPickerOpen(false);
                      }}
                    >
                      <span className="step-label">
                        {d === 0 ? "Surface (0m)" : `${d} m`}
                      </span>
                      {isSelected && <span className="step-indicator">●</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </aside>
  );
};
