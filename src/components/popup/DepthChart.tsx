import React, { useState } from 'react';
import type { OceanProfile } from '../../api/types';

interface DepthChartProps {
  profile: OceanProfile;
  variable: string;
  fieldLabel: string;
  fieldUnit: string;
}

export function DepthChart({ profile, variable, fieldLabel, fieldUnit }: DepthChartProps) {
  const [selectedDepthIdx, setSelectedDepthIdx] = useState<number | null>(null);

  const width = 280;
  const height = 300;
  const padding = { top: 32, right: 24, bottom: 20, left: 24 };

  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const dataPoints = profile.depths
    .filter(d => d.oceanEmbed?.[variable as keyof typeof d.oceanEmbed] !== undefined)
    .map(d => ({
      depth: d.depth,
      value: d.oceanEmbed![variable as keyof typeof d.oceanEmbed] as number,
      uncertainty: d.oceanEmbed!.uncertainty
    }));

  if (dataPoints.length === 0) {
    return <div style={{ padding: '20px', color: '#99A8A9', fontSize: '12px' }}>No prediction data available for this field.</div>;
  }

  const getY = (index: number) => padding.top + (index / (dataPoints.length - 1 || 1)) * innerHeight;

  const minVal = Math.floor(Math.min(...dataPoints.map(d => d.value)) - 0.5);
  const maxVal = Math.ceil(Math.max(...dataPoints.map(d => d.value)) + 0.5);

  const getX = (val: number) => {
    if (maxVal === minVal) return padding.left + innerWidth / 2;
    return padding.left + ((val - minVal) / (maxVal - minVal)) * innerWidth;
  };

  const pathD = dataPoints.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(d.value)} ${getY(i)}`).join(' ');

  const ticks = [];
  const range = maxVal - minVal;
  const step = range > 10 ? 5 : range > 5 ? 2 : 1;
  for (let v = minVal; v <= maxVal; v += step) {
    ticks.push(v);
  }

  const selectedPt = selectedDepthIdx !== null ? dataPoints[selectedDepthIdx] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="ap-chart-wrapper" style={{ width: '100%', height: `${height}px`, position: 'relative' }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
          <text x={padding.left} y={12} fill="#99A8A9" fontSize="9px" fontFamily="var(--sans)" letterSpacing="0.05em">
            PREDICTED {fieldLabel.toUpperCase()} ({fieldUnit})
          </text>

          {ticks.map(tick => (
            <g key={`tick-${tick}`}>
              <line x1={getX(tick)} y1={padding.top} x2={getX(tick)} y2={height - padding.bottom} stroke="rgba(153, 168, 169, 0.18)" strokeWidth="1" strokeDasharray="2 4" />
              <text x={getX(tick)} y={24} fill="#99A8A9" fontSize="10px" fontFamily="var(--sans)" textAnchor="middle">
                {tick}
              </text>
            </g>
          ))}

          {dataPoints.map((d, i) => {
            const y = getY(i);
            const isSelected = i === selectedDepthIdx;
            return (
              <g key={`depth-grid-${d.depth}`}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke={isSelected ? "#2B5AAF" : "rgba(153, 168, 169, 0.18)"} strokeWidth="1" opacity={isSelected ? 1.0 : 0.6} />
                <text x={padding.left - 4} y={y + 3} fill={isSelected ? "#ADBCC7" : "#99A8A9"} fontSize="10px" fontFamily="var(--sans)" textAnchor="end" fontWeight={isSelected ? 600 : 400}>
                  {d.depth}m
                </text>
              </g>
            );
          })}

          <path d={pathD} fill="none" stroke="#2B5AAF" strokeWidth="2.2" />

          {dataPoints.map((d, i) => (
            <circle 
              key={`pt-${i}`} 
              cx={getX(d.value)} 
              cy={getY(i)} 
              r={i === selectedDepthIdx ? "4.5" : "3.5"} 
              fill={i === selectedDepthIdx ? "#2B5AAF" : "#0A1118"} 
              stroke="#2B5AAF" 
              strokeWidth="1.5" 
            />
          ))}

          {dataPoints.map((d, i) => {
            const cx = getX(d.value);
            const cy = getY(i);
            return (
              <g key={`hover-${i}`} className="chart-hover-group">
                <rect 
                  x={padding.left} 
                  y={cy - 12} 
                  width={innerWidth} 
                  height={24} 
                  fill="transparent" 
                  style={{ cursor: 'pointer' }} 
                  onClick={() => setSelectedDepthIdx(i === selectedDepthIdx ? null : i)}
                />
                <g className="tooltip-overlay" style={{ pointerEvents: 'none', opacity: 0 }}>
                  <circle cx={cx} cy={cy} r="4.5" fill="#2B5AAF" />
                  <rect x={cx + 10} y={cy - 16} width={64} height={32} rx="0" fill="#0E1822" stroke="rgba(153, 168, 169, 0.3)" />
                  <text x={cx + 16} y={cy - 2} fill="#99A8A9" fontSize="9px" fontFamily="var(--sans)" fontWeight="600">{d.depth}m</text>
                  <text x={cx + 16} y={cy + 9} fill="#ADBCC7" fontSize="11px" fontFamily="var(--sans)" fontWeight="500">{d.value.toFixed(2)}</text>
                </g>
              </g>
            );
          })}
        </svg>
      </div>

      {selectedPt && (
        <div style={{
          marginTop: '12px',
          padding: '10px 12px',
          background: '#0E1822',
          border: '1px solid rgba(153, 168, 169, 0.24)',
          borderRadius: '0px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '10px', color: '#99A8A9', fontWeight: 600, letterSpacing: '0.05em' }}>DEPTH</span>
            <span style={{ fontSize: '13.5px', color: '#ADBCC7', fontWeight: 600 }}>{selectedPt.depth}m</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '10px', color: '#99A8A9', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>{fieldLabel}</span>
            <span style={{ fontSize: '13.5px', color: '#ADBCC7', fontWeight: 600 }}>{selectedPt.value.toFixed(2)} {fieldUnit}</span>
          </div>
          {selectedPt.uncertainty !== undefined && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '10px', color: '#99A8A9', fontWeight: 600, letterSpacing: '0.05em' }}>UNCERTAINTY</span>
              <span style={{ fontSize: '13.5px', color: '#ADBCC7', fontWeight: 600 }}>± {selectedPt.uncertainty.toFixed(2)} σ</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
