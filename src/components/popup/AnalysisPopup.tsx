import React, { useState, useEffect, useRef } from 'react';
import type { Map } from 'maplibre-gl';
import type { Coordinate, OceanProfile } from '../../api/types';
import { geoService } from '../../services/GeospatialService';
import { DepthChart } from './DepthChart';

interface AnalysisPopupProps {
  map: Map | null;
  selected: Coordinate;
  date: string;
  fieldId: string;
  fieldLabel: string;
  fieldUnit: string;
  isDepthField: boolean;
  profile: OceanProfile | null | undefined;
  panelData: any;
  apiError: string | null;
  onClose: () => void;
}

export function AnalysisPopup({ 
  map, selected, date, fieldId, fieldLabel, fieldUnit, isDepthField, profile, panelData, apiError, onClose 
}: AnalysisPopupProps) {
  const popupRef = useRef<HTMLDivElement>(null);
  
  // Projected map coordinate
  const [anchor, setAnchor] = useState({ x: 0, y: 0 });
  
  // Drag offset from the initial anchor position
  const [offset, setOffset] = useState({ x: 20, y: -40 }); 
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, offsetX: 0, offsetY: 0 });
  
  useEffect(() => {
    if (!map) return;
    
    const updateAnchor = () => {
      const p = map.project([selected.lon, selected.lat]);
      setAnchor({ x: p.x, y: p.y });
      
      const w = window.innerWidth;
      const h = window.innerHeight;
        
        let initialX = p.x + 40;
        let initialY = p.y - 100;
        
        // If near right edge, place on left
        if (p.x > w - 420) {
          initialX = p.x - 420;
        }
        // If near bottom, move up
        if (p.y > h - 400) {
          initialY = p.y - 450;
        }
        // Ensure it doesn't go off top
        if (initialY < 60) {
          initialY = 80;
        }
        
      // Only set offset if we haven't touched it (simplistic heuristic, better handled by drag logic)
    };
    
    updateAnchor();
    
    map.on('move', updateAnchor);
    return () => {
      map.off('move', updateAnchor);
    };
  }, [map, selected]);


  const handlePointerDown = (e: React.PointerEvent) => {
    isDragging.current = true;
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      offsetX: offset.x,
      offsetY: offset.y
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setOffset({
      x: dragStart.current.offsetX + dx,
      y: dragStart.current.offsetY + dy
    });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    isDragging.current = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  const popupX = anchor.x + offset.x;
  const popupY = anchor.y + offset.y;

  // Connector math
  // We want to connect anchor(x,y) to the nearest edge/corner of the popup rect
  // For simplicity, connect to the center of the popup bounding box
  // Anchor the connector line to the top-left of the popup just below the header

  const formatCoord = (c: Coordinate) => `${c.lat.toFixed(2)}°N, ${c.lon.toFixed(2)}°E`;

  return (
    <>
      {/* SVG Connector Layer */}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 10 }}>
          <>
            <line 
              x1={anchor.x} y1={anchor.y} 
              x2={popupX + 20} y2={popupY + 36} 
              stroke="#2B5AAF" strokeWidth="1.2" opacity={1.0} 
            />
            {/* Map point marker */}
            <circle cx={anchor.x} cy={anchor.y} r="3.5" fill="#0A1118" stroke="#2B5AAF" strokeWidth="1.5" />
          </>
      </svg>

      {/* Draggable Popup */}
      <div 
        ref={popupRef}
        className="analysis-popup"
        style={{ 
          position: 'absolute', 
          left: 0, 
          top: 0, 
          transform: `translate(${popupX}px, ${popupY}px)`,
          zIndex: 11,
          opacity: 1
        }}
        onPointerDown={(e) => e.stopPropagation()} 
        onWheel={(e) => e.stopPropagation()} 
      >
        <div 
          className="ap-header" 
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <div className="ap-title">
            OCEAN · {formatCoord(selected)}
          </div>
          <div className="ap-close" onClick={onClose} onPointerDown={(e) => e.stopPropagation()}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </div>
        </div>

        <div className="ap-meta">
          <div className="ap-date">{date}</div>
          {profile?.nearestArgoKm !== undefined && (
            <div className="ap-argo-dist">nearest ARGO {profile.nearestArgoKm.toFixed(0)} km</div>
          )}
        </div>

        <div className="ap-body">
          {geoService.isLand(selected.lat, selected.lon) ? (
            <div className="ap-error">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 8, stroke: '#99A8A9' }}>
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              LAND SELECTED
              <br/>
              <span>Prediction models strictly exclude terrestrial zones.</span>
            </div>
          ) : !geoService.isInDomain(selected.lat, selected.lon) ? (
            <div className="ap-error">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 8, stroke: '#99A8A9' }}>
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              OUTSIDE DOMAIN
              <br/>
              <span>Coordinates exceed current model boundaries.</span>
              <div className="ap-domain-box">
                Active Domain: 5°N–30°N, 45°E–105°E
              </div>
            </div>
          ) : apiError ? (
            <div className="ap-error">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 8, stroke: '#FF5C63' }}>
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              PREDICTION UNAVAILABLE
              <br/>
              <span style={{ color: '#FF5C63' }}>{apiError}</span>
            </div>
          ) : (isDepthField && fieldId !== 'uncertainty' && profile === undefined) || ((!isDepthField || fieldId === 'uncertainty') && panelData === undefined) ? (
            <div className="ap-loading">
              <div className="ap-spinner"></div>
              PREDICTING...
            </div>
          ) : isDepthField && fieldId !== 'uncertainty' && profile ? (
            <>
              <div className="ap-chart-header">
                <div className="ap-chart-title">DEPTH PROFILE</div>
                <div className="ap-chart-field">{fieldLabel}</div>
                <div className="ap-chart-unit">{fieldUnit}</div>
              </div>
              <DepthChart profile={profile} variable={fieldId} fieldLabel={fieldLabel} fieldUnit={fieldUnit} />
              <div className="ap-chart-legend">
                <div className="ap-legend-circle"></div> OceanEmbed prediction
              </div>
            </>
          ) : fieldId === 'uncertainty' && panelData ? (
            <div className="ap-scalar-card">
              <div className="ap-chart-title">UNCERTAINTY ESTIMATES</div>
              <div className="ap-chart-field">{panelData.depth}m DEPTH</div>
              <div style={{ display: 'flex', gap: '24px', marginTop: '16px' }}>
                <div>
                  <div style={{ fontSize: '10px', color: '#99A8A9', fontWeight: 600, letterSpacing: '0.05em' }}>TEMPERATURE</div>
                  <div className="ap-scalar-value" style={{ marginTop: '4px' }}>
                    ± {panelData.tempUncertainty?.toFixed(3)} <span>σ °C</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', color: '#99A8A9', fontWeight: 600, letterSpacing: '0.05em' }}>SALINITY</div>
                  <div className="ap-scalar-value" style={{ marginTop: '4px' }}>
                    ± {panelData.salUncertainty?.toFixed(3)} <span>σ psu</span>
                  </div>
                </div>
              </div>
            </div>
          ) : !isDepthField && panelData ? (
            <div className="ap-scalar-card">
              <div className="ap-chart-title">SURFACE PREDICTION</div>
              <div className="ap-chart-field">{fieldLabel}</div>
              <div className="ap-scalar-value">
                {panelData.value?.toFixed(2)} <span>{fieldUnit}</span>
              </div>
            </div>
          ) : (
            <div className="ap-error">PREDICTION UNAVAILABLE</div>
          )}
        </div>
      </div>
    </>
  );
}
