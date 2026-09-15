import React, { useState, useEffect, useRef } from "react";
import type { Map as MapLibreInstance } from "maplibre-gl";
import type { SelectedLocation, GraphCardCluster } from "../../types/comparison";
import { LocationGraphCard } from "./LocationGraphCard";
import { MergedComparisonCard } from "./MergedComparisonCard";
import { geoService } from "../../services/GeospatialService";

interface CardsManagerProps {
  map: MapLibreInstance | null;
  clusters: GraphCardCluster[];
  locations: SelectedLocation[];
  date: string;
  fieldId: string;
  fieldLabel: string;
  fieldUnit: string;
  isDepthField: boolean;
  panelData?: any;
  apiError: string | null;
  justMergedClusterId: string | null;
  onMergeClusters: (sourceClusterId: string, targetClusterId: string) => void;
  onSplitCluster: (clusterId: string) => void;
  onDetachLocation: (clusterId: string, locId: string) => void;
  onRemoveCluster: (clusterId: string) => void;
  onRemoveLocation: (locId: string) => void;
  onUpdateClusterOffset: (clusterId: string, offset: { x: number; y: number }) => void;
}

export function CardsManager({
  map,
  clusters,
  locations,
  date,
  fieldId,
  fieldLabel,
  fieldUnit,
  isDepthField,
  panelData,
  apiError,
  justMergedClusterId,
  onMergeClusters,
  onSplitCluster,
  onDetachLocation,
  onRemoveCluster,
  onRemoveLocation,
  onUpdateClusterOffset,
}: CardsManagerProps) {
  const [, setMapTick] = useState(0);

  // Dragging state
  const [draggedClusterId, setDraggedClusterId] = useState<string | null>(null);
  const [dropTargetClusterId, setDropTargetClusterId] = useState<string | null>(null);

  const dragStartInfo = useRef<{
    clusterId: string;
    startX: number;
    startY: number;
    initialOffset: { x: number; y: number };
  } | null>(null);

  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Helper to check if a cluster contains any land location
  const isClusterLand = (cId: string | null): boolean => {
    if (!cId) return false;
    const c = clusters.find((item) => item.id === cId);
    if (!c) return false;
    return c.locationIds.some((lid) => {
      const loc = locations.find((l) => l.id === lid);
      return loc ? geoService.isLand(loc.coord.lat, loc.coord.lon) : false;
    });
  };

  // Listen to map movements to re-render leader lines
  useEffect(() => {
    if (!map) return;
    const handleMapUpdate = () => setMapTick((t) => t + 1);
    map.on("move", handleMapUpdate);
    map.on("zoom", handleMapUpdate);
    map.on("resize", handleMapUpdate);
    return () => {
      map.off("move", handleMapUpdate);
      map.off("zoom", handleMapUpdate);
      map.off("resize", handleMapUpdate);
    };
  }, [map]);

  const handlePointerDownDrag = (clusterId: string, e: React.PointerEvent) => {
    // If this cluster contains land, do not allow dragging to merge
    if (isClusterLand(clusterId)) return;

    const cluster = clusters.find((c) => c.id === clusterId);
    if (!cluster) return;

    dragStartInfo.current = {
      clusterId,
      startX: e.clientX,
      startY: e.clientY,
      initialOffset: { ...cluster.offset },
    };
    setDraggedClusterId(clusterId);
    try {
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  const handlePointerMoveDrag = (e: React.PointerEvent) => {
    if (!dragStartInfo.current) return;
    const { clusterId, startX, startY, initialOffset } = dragStartInfo.current;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    const newOffset = {
      x: initialOffset.x + dx,
      y: initialOffset.y + dy,
    };
    onUpdateClusterOffset(clusterId, newOffset);

    // If source cluster is land, cannot merge onto anything
    if (isClusterLand(clusterId)) {
      setDropTargetClusterId(null);
      return;
    }

    // Collision detection: Check if cursor or card overlaps any other cluster card
    let targetId: string | null = null;
    cardRefs.current.forEach((el, id) => {
      if (id === clusterId || !el) return;

      // DO NOT allow dropping onto a land cluster
      if (isClusterLand(id)) return;

      const rect = el.getBoundingClientRect();
      const margin = 10; // hit margin
      if (
        e.clientX >= rect.left - margin &&
        e.clientX <= rect.right + margin &&
        e.clientY >= rect.top - margin &&
        e.clientY <= rect.bottom + margin
      ) {
        targetId = id;
      }
    });

    setDropTargetClusterId(targetId);
  };

  const handlePointerUpDrag = (e: React.PointerEvent) => {
    if (!dragStartInfo.current) return;
    const { clusterId } = dragStartInfo.current;

    if (
      dropTargetClusterId &&
      dropTargetClusterId !== clusterId &&
      !isClusterLand(clusterId) &&
      !isClusterLand(dropTargetClusterId)
    ) {
      onMergeClusters(clusterId, dropTargetClusterId);
    }

    dragStartInfo.current = null;
    setDraggedClusterId(null);
    setDropTargetClusterId(null);
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  };

  if (!map) return null;

  // Compute leader lines data
  const leaderLines: Array<{
    id: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    color: string;
  }> = [];

  const locationMap = new Map<string, SelectedLocation>();
  locations.forEach((loc) => locationMap.set(loc.id, loc));

  // Find dragged location label for drop target preview
  const draggedCluster = clusters.find((c) => c.id === draggedClusterId);
  let draggedLocationLabel = "";
  if (draggedCluster) {
    const clusterLocs = draggedCluster.locationIds
      .map((id) => locationMap.get(id)?.label)
      .filter(Boolean);
    draggedLocationLabel = clusterLocs.join("+");
  }

  return (
    <div
      className="cards-manager-container"
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 20,
        overflow: "hidden",
      }}
      onPointerMove={draggedClusterId ? handlePointerMoveDrag : undefined}
      onPointerUp={draggedClusterId ? handlePointerUpDrag : undefined}
    >
      {/* SVG Leader Lines Layer */}
      <svg
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 1,
        }}
      >
        {clusters.map((cluster) => {
          const clusterLocs = cluster.locationIds
            .map((id) => locationMap.get(id))
            .filter((l): l is SelectedLocation => Boolean(l));
          if (clusterLocs.length === 0) return null;

          // Anchor point from primary location
          const primaryLoc = clusterLocs[0];
          const anchor = map.project([primaryLoc.coord.lon, primaryLoc.coord.lat]);
          const cardX = anchor.x + cluster.offset.x;
          const cardY = anchor.y + cluster.offset.y;

          return clusterLocs.map((loc, idx) => {
            const origin = map.project([loc.coord.lon, loc.coord.lat]);
            // Target point on the card: top-left corner below header
            const targetX = cardX + 12;
            const targetY = cardY + 24 + idx * 4;

            return (
              <g key={`leader-${cluster.id}-${loc.id}`}>
                {/* Dark underlay for maximum contrast against any raster */}
                <line
                  x1={origin.x}
                  y1={origin.y}
                  x2={targetX}
                  y2={targetY}
                  stroke="#060C14"
                  strokeWidth="3.4"
                  strokeDasharray="5 3.5"
                  opacity={0.85}
                />
                {/* Dark bold dotted leader line */}
                <line
                  x1={origin.x}
                  y1={origin.y}
                  x2={targetX}
                  y2={targetY}
                  stroke="#1A3B70"
                  strokeWidth="2.2"
                  strokeDasharray="5 3.5"
                  opacity={1.0}
                />
              </g>
            );
          });
        })}
      </svg>

      {/* Render Each Cluster Card */}
      {clusters.map((cluster) => {
        const clusterLocs = cluster.locationIds
          .map((id) => locationMap.get(id))
          .filter((l): l is SelectedLocation => Boolean(l));

        if (clusterLocs.length === 0) return null;

        const primaryLoc = clusterLocs[0];
        const anchor = map.project([primaryLoc.coord.lon, primaryLoc.coord.lat]);
        const cardX = anchor.x + cluster.offset.x;
        const cardY = anchor.y + cluster.offset.y;

        const isDraggingThis = draggedClusterId === cluster.id;
        const isDropTarget = dropTargetClusterId === cluster.id;
        const justMerged = justMergedClusterId === cluster.id;

        return (
          <div
            key={cluster.id}
            ref={(el) => {
              if (el) cardRefs.current.set(cluster.id, el);
              else cardRefs.current.delete(cluster.id);
            }}
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              transform: `translate(${cardX}px, ${cardY}px)`,
              pointerEvents: "auto",
              zIndex: isDraggingThis ? 100 : isDropTarget ? 50 : 25,
            }}
          >
            {cluster.isMerged || clusterLocs.length >= 2 ? (
              <MergedComparisonCard
                locations={clusterLocs}
                date={date}
                fieldId={fieldId}
                fieldLabel={fieldLabel}
                fieldUnit={fieldUnit}
                onClose={() => onRemoveCluster(cluster.id)}
                onSplitAll={() => onSplitCluster(cluster.id)}
                onDetachLocation={(locId) => onDetachLocation(cluster.id, locId)}
                onRemoveLocation={(locId) => onRemoveLocation(locId)}
                onPointerDownDrag={(e) => handlePointerDownDrag(cluster.id, e)}
                isDraggingThis={isDraggingThis}
                isDropTarget={isDropTarget}
                draggedLocationLabel={draggedLocationLabel}
                justMerged={justMerged}
              />
            ) : (
              <LocationGraphCard
                location={clusterLocs[0]}
                date={date}
                fieldId={fieldId}
                fieldLabel={fieldLabel}
                fieldUnit={fieldUnit}
                isDepthField={isDepthField}
                panelData={panelData}
                apiError={apiError}
                onClose={() => onRemoveLocation(clusterLocs[0].id)}
                onPointerDownDrag={(e) => handlePointerDownDrag(cluster.id, e)}
                isDraggingThis={isDraggingThis}
                isDropTarget={isDropTarget}
                draggedLocationLabel={draggedLocationLabel}
                justMerged={justMerged}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
