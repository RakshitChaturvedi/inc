import type { Coordinate, OceanProfile } from "../api/types";

export interface SelectedLocation {
  id: string;
  label: string; // "A", "B", "C", "D", "E", "F"
  coord: Coordinate;
  color: string;
  inComparison: boolean;
  profile?: OceanProfile | null;
  loading?: boolean;
}

export const LOCATION_LABELS = ["A", "B", "C", "D", "E", "F"] as const;

export const LOCATION_COLORS = [
  "#2B5AAF", // Series A: Primary Accent
  "#99A8A9", // Series B: Secondary Neutral
  "#ADBCC7", // Series C: Primary Light
  "#557CA8", // Series D: Muted Slate Blue
  "#7D929D", // Series E: Muted Cadet Slate
  "#C0CCD6", // Series F: Cool Light Mist
] as const;

export const MAX_LOCATIONS = 6;

export interface GraphCardCluster {
  id: string;
  locationIds: string[];
  offset: { x: number; y: number };
  isMerged: boolean;
}
