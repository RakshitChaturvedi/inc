import React, { useState } from "react";
import type { SelectedLocation } from "../../types/comparison";
import { DEPTHS } from "../../api/types";

interface ComparisonChartProps {
  locations: SelectedLocation[];
  variable: string;
  fieldLabel: string;
  fieldUnit: string;
  isZoomed?: boolean;
}

export function ComparisonChart({
  locations,
  variable,
  fieldLabel,
  fieldUnit,
  isZoomed = false,
}: ComparisonChartProps) {
  const [hoveredPoint, setHoveredPoint] = useState<{
    locLabel: string;
    locColor: string;
    depth: number;
    value: number;
    x: number;
    y: number;
  } | null>(null);

  const width = isZoomed ? 640 : 420;
  const height = isZoomed ? 450 : 340;
  const padding = isZoomed
    ? { top: 32, right: 32, bottom: 24, left: 44 }
    : { top: 28, right: 24, bottom: 22, left: 38 };

  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  // Extract all valid points across all locations
  const seriesData = locations.map((loc) => {
    if (!loc.profile || !loc.profile.depths) {
      return { loc, points: [] };
    }
    const points = loc.profile.depths
      .filter((d) => d.oceanEmbed?.[variable as keyof typeof d.oceanEmbed] !== undefined)
      .map((d) => ({
        depth: d.depth,
        value: d.oceanEmbed![variable as keyof typeof d.oceanEmbed] as number,
      }));
    return { loc, points };
  });

  const allValues = seriesData.flatMap((s) => s.points.map((p) => p.value));
  const allDepths: number[] =
    seriesData.length > 0 && seriesData[0].points.length > 0
      ? seriesData[0].points.map((p) => p.depth)
      : (DEPTHS as unknown as number[]);

  if (allValues.length === 0) {
    return (
      <div style={{ padding: "24px", color: "#99A8A9", fontSize: "12px", textAlign: "center" }}>
        Loading comparison prediction data...
      </div>
    );
  }

  const minVal = Math.floor(Math.min(...allValues) - 0.5);
  const maxVal = Math.ceil(Math.max(...allValues) + 0.5);

  const getY = (index: number) =>
    padding.top + (index / (allDepths.length - 1 || 1)) * innerHeight;

  const getX = (val: number) => {
    if (maxVal === minVal) return padding.left + innerWidth / 2;
    return padding.left + ((val - minVal) / (maxVal - minVal)) * innerWidth;
  };

  // Generate X ticks
  const ticks = [];
  const range = maxVal - minVal;
  const step = range > 10 ? 5 : range > 5 ? 2 : 1;
  for (let v = minVal; v <= maxVal; v += step) {
    ticks.push(v);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%" }}>
      {/* SVG Multi-Series Chart */}
      <div style={{ width: "100%", height: `${height}px`, position: "relative" }}>
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${width} ${height}`}
          style={{ overflow: "visible" }}
        >
          {/* Chart Header Axis Label */}
          <text
            x={padding.left}
            y={12}
            fill="#99A8A9"
            fontSize="9px"
            fontFamily="var(--sans)"
            letterSpacing="0.05em"
          >
            PREDICTED {fieldLabel.toUpperCase()} ({fieldUnit})
          </text>

          {/* Vertical Grid & X Values */}
          {ticks.map((tick) => (
            <g key={`tick-${tick}`}>
              <line
                x1={getX(tick)}
                y1={padding.top}
                x2={getX(tick)}
                y2={height - padding.bottom}
                stroke="rgba(153, 168, 169, 0.16)"
                strokeWidth="1"
                strokeDasharray="2 4"
              />
              <text
                x={getX(tick)}
                y={22}
                fill="#99A8A9"
                fontSize="9.5px"
                fontFamily="var(--sans)"
                textAnchor="middle"
              >
                {tick}
              </text>
            </g>
          ))}

          {/* Horizontal Depth Grid & Y Values: ALL 15 DEPTHS */}
          {allDepths.map((d, i) => {
            const y = getY(i);
            const isHoveredDepth = hoveredPoint?.depth === d;
            return (
              <g key={`depth-${d}`}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke={isHoveredDepth ? "#2B5AAF" : "rgba(153, 168, 169, 0.18)"}
                  strokeWidth="1"
                  opacity={isHoveredDepth ? 0.95 : 0.55}
                />
                <text
                  x={padding.left - 5}
                  y={y + 3}
                  fill={isHoveredDepth ? "#ADBCC7" : "#99A8A9"}
                  fontSize={isZoomed ? "9.5px" : "8.5px"}
                  fontFamily="var(--sans)"
                  fontWeight={isHoveredDepth ? 600 : 400}
                  textAnchor="end"
                >
                  {d}m
                </text>
              </g>
            );
          })}

          {/* Lines for each location */}
          {seriesData.map(({ loc, points }) => {
            if (points.length === 0) return null;
            const pathD = points
              .map((p, i) => `${i === 0 ? "M" : "L"} ${getX(p.value)} ${getY(i)}`)
              .join(" ");

            return (
              <g key={`series-${loc.id}`}>
                {/* Prediction line */}
                <path
                  d={pathD}
                  fill="none"
                  stroke={loc.color}
                  strokeWidth={isZoomed ? "2.5" : "2"}
                  opacity={0.9}
                />

                {/* Data points */}
                {points.map((p, i) => {
                  const cx = getX(p.value);
                  const cy = getY(i);
                  const isHovered =
                    hoveredPoint?.locLabel === loc.label && hoveredPoint?.depth === p.depth;

                  return (
                    <circle
                      key={`pt-${loc.id}-${p.depth}`}
                      cx={cx}
                      cy={cy}
                      r={isHovered ? (isZoomed ? 6 : 4.5) : (isZoomed ? 4 : 3)}
                      fill={isHovered ? loc.color : "#0A1118"}
                      stroke={loc.color}
                      strokeWidth={isZoomed ? "2" : "1.5"}
                      style={{ cursor: "pointer" }}
                      onMouseEnter={() =>
                        setHoveredPoint({
                          locLabel: loc.label,
                          locColor: loc.color,
                          depth: p.depth,
                          value: p.value,
                          x: cx,
                          y: cy,
                        })
                      }
                      onMouseLeave={() => setHoveredPoint(null)}
                    />
                  );
                })}
              </g>
            );
          })}

          {/* Interactive Hover Tooltip */}
          {hoveredPoint && (
            <g
              transform={`translate(${hoveredPoint.x > width - 100 ? hoveredPoint.x - 90 : hoveredPoint.x + 8}, ${hoveredPoint.y - 32})`}
              style={{ pointerEvents: "none" }}
            >
              <rect
                x="0"
                y="0"
                width="84"
                height="32"
                fill="#0E1822"
                stroke="rgba(153, 168, 169, 0.35)"
                rx="0"
              />
              <text
                x="6"
                y="12"
                fill={hoveredPoint.locColor}
                fontSize="9.5px"
                fontFamily="var(--sans)"
                fontWeight="700"
              >
                LOC {hoveredPoint.locLabel} · {hoveredPoint.depth}m
              </text>
              <text
                x="6"
                y="24"
                fill="#ADBCC7"
                fontSize="10.5px"
                fontFamily="var(--sans)"
                fontWeight="600"
              >
                {hoveredPoint.value.toFixed(2)} {fieldUnit}
              </text>
            </g>
          )}
        </svg>
      </div>

      {/* Comparison Series Legend */}
      <div className="comp-chart-legend">
        {locations.map((loc) => (
          <div key={loc.id} className="comp-legend-chip">
            <span
              className="comp-legend-dot"
              style={{ background: loc.color }}
            />
            <span className="comp-legend-label" style={{ color: loc.color }}>
              {loc.label}
            </span>
            <span className="comp-legend-coord">
              {loc.coord.lat.toFixed(2)}°N, {loc.coord.lon.toFixed(2)}°E
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
