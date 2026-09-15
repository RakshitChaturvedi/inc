import React from "react";
import type { BasemapId } from "../../map/basemaps";
import type { RunStatus } from "../../api/types";

interface WindyMenuDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  basemap: BasemapId;
  onChangeBasemap: (basemap: BasemapId) => void;
  showGrid: boolean;
  onToggleGrid: (show: boolean) => void;
  showArgo: boolean;
  onToggleArgo: (show: boolean) => void;
  showSampling: boolean;
  onToggleSampling: (show: boolean) => void;
  showSaliency?: boolean;
  onToggleSaliency?: (show: boolean) => void;
  status?: RunStatus;
  analysisDate: string;
}

export const WindyMenuDrawer: React.FC<WindyMenuDrawerProps> = ({
  isOpen,
  onClose,
  basemap,
  onChangeBasemap,
  showGrid,
  onToggleGrid,
  showArgo,
  onToggleArgo,
  showSampling,
  onToggleSampling,
  status,
  analysisDate,
}) => {
  if (!isOpen) return null;

  return (
    <div className="windy-drawer-overlay" onClick={onClose}>
      <aside
        className="windy-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Application Menu"
      >
        {/* Header with red circular logo/icon */}
        <div className="windy-drawer-header">
          <div className="windy-drawer-title-group">
            <div className="windy-red-circle-badge">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </div>
            <div>
              <h2 className="windy-drawer-title">OceanEmbed</h2>
              <span className="windy-drawer-subtitle">Reconstruction & Diagnostics</span>
            </div>
          </div>
          <button
            type="button"
            className="windy-drawer-close"
            onClick={onClose}
            aria-label="Close menu"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="windy-drawer-body">
          {/* BASEMAP SECTION */}
          <div className="windy-drawer-section">
            <div className="windy-section-title">BASEMAP LAYER</div>
            <div className="windy-basemap-grid">
              <button
                type="button"
                className={`windy-basemap-card ${basemap === "basic" ? "active" : ""}`}
                onClick={() => onChangeBasemap("basic")}
              >
                <div className="windy-basemap-preview basic-preview">
                  <div className="preview-ocean"></div>
                  <div className="preview-land"></div>
                </div>
                <div className="windy-basemap-card-info">
                  <span className="windy-card-name">Carto Dark</span>
                  <span className="windy-card-desc">High-contrast oceanic basemap</span>
                </div>
                {basemap === "basic" && <span className="windy-check-dot">✓</span>}
              </button>

              <button
                type="button"
                className={`windy-basemap-card ${basemap === "satellite" ? "active" : ""}`}
                onClick={() => onChangeBasemap("satellite")}
              >
                <div className="windy-basemap-preview sat-preview">
                  <div className="preview-sat-clouds"></div>
                </div>
                <div className="windy-basemap-card-info">
                  <span className="windy-card-name">Satellite</span>
                  <span className="windy-card-desc">Global true-color imagery</span>
                </div>
                {basemap === "satellite" && <span className="windy-check-dot">✓</span>}
              </button>
            </div>
          </div>

          <div className="windy-divider"></div>

          {/* OVERLAYS SECTION */}
          <div className="windy-drawer-section">
            <div className="windy-section-title">MAP OVERLAYS & SENSORS</div>

            <div className="windy-toggle-item" onClick={() => onToggleGrid(!showGrid)}>
              <div className="windy-toggle-left">
                <div className="windy-icon-box grid-box">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <line x1="3" y1="9" x2="21" y2="9" />
                    <line x1="3" y1="15" x2="21" y2="15" />
                    <line x1="9" y1="3" x2="9" y2="21" />
                    <line x1="15" y1="3" x2="15" y2="21" />
                  </svg>
                </div>
                <div>
                  <div className="windy-toggle-name">0.25° Model Grid</div>
                  <div className="windy-toggle-desc">High-resolution lat/lon spatial cell mesh</div>
                </div>
              </div>
              <div className={`windy-switch ${showGrid ? "active" : ""}`}>
                <div className="windy-switch-thumb" />
              </div>
            </div>

            <div className="windy-toggle-item" onClick={() => onToggleArgo(!showArgo)}>
              <div className="windy-toggle-left">
                <div className="windy-icon-box argo-box">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div>
                  <div className="windy-toggle-name">ARGO Float Profilers</div>
                  <div className="windy-toggle-desc">Live autonomous depth float observations</div>
                </div>
              </div>
              <div className={`windy-switch ${showArgo ? "active" : ""}`}>
                <div className="windy-switch-thumb" />
              </div>
            </div>

            <div className="windy-toggle-item" onClick={() => onToggleSampling(!showSampling)}>
              <div className="windy-toggle-left">
                <div className="windy-icon-box sample-box">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="22" y1="12" x2="18" y2="12" />
                    <line x1="6" y1="12" x2="2" y2="12" />
                    <line x1="12" y1="6" x2="12" y2="2" />
                    <line x1="12" y1="22" x2="12" y2="18" />
                  </svg>
                </div>
                <div>
                  <div className="windy-toggle-name">Suggested Sampling</div>
                  <div className="windy-toggle-desc">Optimal candidate points to minimize uncertainty</div>
                </div>
              </div>
              <div className={`windy-switch ${showSampling ? "active" : ""}`}>
                <div className="windy-switch-thumb" />
              </div>
            </div>

            <div className="windy-toggle-item disabled">
              <div className="windy-toggle-left">
                <div className="windy-icon-box saliency-box">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div>
                  <div className="windy-toggle-name">AI Saliency Gradients</div>
                  <div className="windy-toggle-desc">Neural attention attribution (Planned)</div>
                </div>
              </div>
              <span className="windy-badge-pill">Soon</span>
            </div>
          </div>

          <div className="windy-divider"></div>

          {/* RUN METADATA SECTION */}
          <div className="windy-drawer-section">
            <div className="windy-section-title">MODEL RUN DIAGNOSTICS</div>
            <div className="windy-meta-card">
              <div className="windy-meta-row">
                <span className="windy-meta-label">Selected Date</span>
                <span className="windy-meta-val">{analysisDate}</span>
              </div>
              <div className="windy-meta-row">
                <span className="windy-meta-label">Analysis Cycle</span>
                <span className="windy-meta-val">{status?.analysisWeek ?? "Weekly Assimilation"}</span>
              </div>
              <div className="windy-meta-row">
                <span className="windy-meta-label">Model Pipeline</span>
                <span className="windy-meta-val">{status?.modelVersion ?? "OceanEmbed v2.4 (GNN-Transformer)"}</span>
              </div>
              <div className="windy-meta-row">
                <span className="windy-meta-label">Quality Gate</span>
                <span className="windy-meta-badge published">
                  {status?.gateStatus ? status.gateStatus.toUpperCase() : "PUBLISHED"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
};
