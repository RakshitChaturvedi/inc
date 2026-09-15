import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { MapMouseEvent } from "maplibre-gl";
import { basemaps, type BasemapId } from "./basemaps";
import type { ArgoFloat, Coordinate, FieldId, FieldPoint, OceanProfile } from "../api/types";
import type { SelectedLocation, GraphCardCluster } from "../types/comparison";
import { CardsManager } from "../components/cards/CardsManager";
import { MapMarkersOverlay } from "../components/map/MapMarkersOverlay";

import { MapboxOverlay } from '@deck.gl/mapbox';
import { BitmapLayer, GeoJsonLayer, ScatterplotLayer, LineLayer } from '@deck.gl/layers';
import { MaskExtension } from '@deck.gl/extensions';
import { geoService } from "../services/GeospatialService";

type Props = { 
  basemap: BasemapId; 
  field: FieldId; 
  points: FieldPoint[]; 
  floats: ArgoFloat[]; 
  showGrid: boolean; 
  showArgo: boolean; 
  showSampling: boolean; 
  showSaliency: boolean; 
  selectedLocations: SelectedLocation[];
  clusters: GraphCardCluster[];
  onSelect: (point: Coordinate) => void;
  onToggleLocation: (loc: SelectedLocation) => void;
  date: string;
  fieldLabel: string;
  fieldUnit: string;
  isDepthField: boolean;
  panelData: any;
  apiError: string | null;
  justMergedClusterId: string | null;
  onMergeClusters: (sourceClusterId: string, targetClusterId: string) => void;
  onSplitCluster: (clusterId: string) => void;
  onDetachLocation: (clusterId: string, locId: string) => void;
  onRemoveCluster: (clusterId: string) => void;
  onRemoveLocation: (locId: string) => void;
  onUpdateClusterOffset: (clusterId: string, offset: { x: number; y: number }) => void;
};

function interpolateColor(val: number, stops: [number, string][]): [number, number, number, number] {
  if (val <= stops[0][0]) return hexToRgb(stops[0][1]);
  if (val >= stops[stops.length - 1][0]) return hexToRgb(stops[stops.length - 1][1]);
  for (let i = 0; i < stops.length - 1; i++) {
    if (val >= stops[i][0] && val <= stops[i+1][0]) {
      const t = (val - stops[i][0]) / (stops[i+1][0] - stops[i][0]);
      const c1 = hexToRgb(stops[i][1]);
      const c2 = hexToRgb(stops[i+1][1]);
      return [
        Math.round(c1[0] + (c2[0] - c1[0]) * t),
        Math.round(c1[1] + (c2[1] - c1[1]) * t),
        Math.round(c1[2] + (c2[2] - c1[2]) * t),
        255
      ];
    }
  }
  return [0, 0, 0, 0];
}

const hexCache: Record<string, [number, number, number]> = {};
function hexToRgb(hex: string): [number, number, number, number] {
  if (hex === "rgba(0,0,0,0)" || hex === "transparent") return [0,0,0,0];
  if (hexCache[hex]) return [...hexCache[hex], 255];
  const m = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  if (m) {
    const rgb = [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] as [number, number, number];
    hexCache[hex] = rgb;
    return [...rgb, 255];
  }
  return [0,0,0,0];
}

const colorStops: Record<FieldId, [number, string][]> = {
  temperature: [[3, "#153c85"], [17, "#18a7c8"], [25, "#64dfc9"], [31, "#ffca65"]],
  salinity: [[31, "#d9e8e8"], [34, "#4ed3d0"], [37, "#4b2b73"]],
  uncertainty: [[0.1, "#133c5b"], [0.6, "#55d6c2"], [1.2, "#ff785a"]],
  tchp: [[10, "#113b62"], [70, "#31c8c9"], [130, "#ffe17b"]],
  d26: [[10, "#1d4b77"], [85, "#43cfbe"], [160, "#f4da7a"]],
  mld: [[10, "#1d4b77"], [85, "#43cfbe"], [160, "#f4da7a"]]
};

function generateImageData(points: FieldPoint[], field: FieldId) {
  const width = 241;
  const height = 101;
  const data = new Uint8ClampedArray(width * height * 4);
  const stops = colorStops[field];

  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    const x = Math.round((p.lon - 45) / 0.25);
    const y = 100 - Math.round((p.lat - 5) / 0.25);
    const idx = (y * width + x) * 4;
    const color = interpolateColor(p.value, stops);
    data[idx] = color[0];
    data[idx+1] = color[1];
    data[idx+2] = color[2];
    data[idx+3] = color[3];
  }
  return new ImageData(data, width, height);
}

type GridLine = { source: [number, number], target: [number, number], level: 5 | 1 | 0.25 };
const gridLines: GridLine[] = [];

for (let lat = 5; lat <= 30; lat += 0.25) {
  let level: 5 | 1 | 0.25 = 0.25;
  if (lat % 1 === 0) level = 1;
  if (lat % 5 === 0) level = 5;
  gridLines.push({ source: [45, lat], target: [105, lat], level });
}

for (let lon = 45; lon <= 105; lon += 0.25) {
  let level: 5 | 1 | 0.25 = 0.25;
  if (lon % 1 === 0) level = 1;
  if (lon % 5 === 0) level = 5;
  gridLines.push({ source: [lon, 5], target: [lon, 30], level });
}

const DOMAIN_BOUNDS: [[number, number], [number, number]] = [[44.8, 4.8], [105.2, 30.2]];

function fitDomain(map: maplibregl.Map) {
  map.fitBounds(DOMAIN_BOUNDS, {
    padding: { top: 66, bottom: 56, left: 64, right: 96 },
    duration: 0,
  });
}

export function OceanMap({ 
  basemap, field, points, floats, showGrid, showArgo, showSampling, showSaliency,
  selectedLocations, clusters, onSelect, onToggleLocation,
  date, fieldLabel, fieldUnit, isDepthField, panelData, apiError,
  justMergedClusterId, onMergeClusters, onSplitCluster, onDetachLocation,
  onRemoveCluster, onRemoveLocation, onUpdateClusterOffset,
}: Props) {
  const node = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapInstance, setMapInstance] = useState<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const activeBasemap = useRef<BasemapId>(basemap);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!node.current || mapRef.current) return;
    const map = new maplibregl.Map({ container: node.current, style: basemaps[basemap], center: [77, 16], zoom: 3.5, maxBounds: [[36, -8], [114, 36]] });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    
    map.on("click", (event: MapMouseEvent) => {
      onSelectRef.current({ lat: event.lngLat.lat, lon: event.lngLat.lng });
    });
    
    map.on("mousemove", (event: MapMouseEvent) => {
      const land = geoService.isLand(event.lngLat.lat, event.lngLat.lng);
      map.getCanvas().style.cursor = land ? "default" : "pointer";
    });

    map.on("load", () => fitDomain(map));

    const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
    map.addControl(overlay as any);
    overlayRef.current = overlay;

    mapRef.current = map;
    setMapInstance(map);

    const handleResize = () => {
      if (mapRef.current) {
        mapRef.current.resize();
        fitDomain(mapRef.current);
      }
    };
    window.addEventListener("resize", handleResize);
    document.addEventListener("fullscreenchange", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      document.removeEventListener("fullscreenchange", handleResize);
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, []);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;

    const layers: any[] = [];

    // Mask layer - renders into stencil buffer
    layers.push(new GeoJsonLayer({
      id: 'land-mask',
      data: '/land.geojson',
      operation: 'mask',
      getFillColor: [255, 255, 255, 255]
    }));

    // Scientific Raster
    if (points.length > 0) {
      const imageData = generateImageData(points, field);
      layers.push(new BitmapLayer({
        id: 'ocean-raster',
        bounds: [44.875, 4.875, 105.125, 30.125] as [number, number, number, number],
        image: imageData,
        _imageCoordinateSystem: 1, // LNGLAT
        extensions: [new MaskExtension()],
        maskId: 'land-mask',
        maskInverted: true
      } as any));
    }

    if (showGrid) {
      layers.push(new LineLayer({
        id: 'model-grid',
        data: gridLines,
        getSourcePosition: d => d.source,
        getTargetPosition: d => d.target,
        getColor: d => {
          if (d.level === 5) return [255, 255, 255, 60];
          if (d.level === 1) return [255, 255, 255, 40];
          return [255, 255, 255, 12];
        },
        getWidth: d => {
          if (d.level === 5) return 1.5;
          if (d.level === 1) return 1.0;
          return 0.5;
        },
        widthUnits: 'pixels',
        extensions: [new MaskExtension()],
        maskId: 'land-mask',
        maskInverted: true
      }));
    }

    // ARGO
    if (showArgo && floats.length > 0) {
      layers.push(new ScatterplotLayer({
        id: 'argo-halo',
        data: floats,
        getPosition: (d: any) => [d.lon, d.lat],
        getFillColor: [79, 216, 230, 36],
        getRadius: 9,
        radiusUnits: 'pixels',
        getLineColor: [220, 233, 239, 255],
        lineWidthUnits: 'pixels',
        getLineWidth: 1,
        stroked: true,
        filled: true,
      }));
      layers.push(new ScatterplotLayer({
        id: 'argo-points',
        data: floats,
        getPosition: (d: any) => [d.lon, d.lat],
        getFillColor: [220, 233, 239, 255],
        getRadius: 3.5,
        radiusUnits: 'pixels',
        getLineColor: [79, 216, 230, 255],
        lineWidthUnits: 'pixels',
        getLineWidth: 1.5,
        stroked: true,
        filled: true,
      }));
    }

    overlay.setProps({ layers });
  }, [points, floats, showArgo, showSampling, showSaliency, field]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (activeBasemap.current === basemap) return;
    activeBasemap.current = basemap;
    map.setStyle(basemaps[basemap]);
  }, [basemap]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={node} className="map-canvas" aria-label="North Indian Ocean reconstruction map" style={{ width: '100%', height: '100%' }} />
      
      {/* Interactive Map Markers for all selected locations */}
      {mapInstance && (
        <MapMarkersOverlay
          map={mapInstance}
          locations={selectedLocations}
          onToggleLocation={onToggleLocation}
        />
      )}

      {/* Floating Graph Cards & Merged Comparison Cards with SVG Leader Lines */}
      {mapInstance && (
        <CardsManager
          map={mapInstance}
          clusters={clusters}
          locations={selectedLocations}
          date={date}
          fieldId={field}
          fieldLabel={fieldLabel}
          fieldUnit={fieldUnit}
          isDepthField={isDepthField}
          panelData={panelData}
          apiError={apiError}
          justMergedClusterId={justMergedClusterId}
          onMergeClusters={onMergeClusters}
          onSplitCluster={onSplitCluster}
          onDetachLocation={onDetachLocation}
          onRemoveCluster={onRemoveCluster}
          onRemoveLocation={onRemoveLocation}
          onUpdateClusterOffset={onUpdateClusterOffset}
        />
      )}
    </div>
  );
}
