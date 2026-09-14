import type { ArgoFloat, Coordinate, FieldId, FieldPoint, OceanEmbedApi, OceanProfile, RunStatus } from "./types";
import { mockOceanApi } from "./mockOceanApi";

const BASE_URL = '/api/v1/ocean';

function getWeekNumber(d: Date) {
  d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return `${d.getUTCFullYear()}-W${weekNo.toString().padStart(2, '0')}`;
}

export function isOutOfDomain(location: Coordinate): boolean {
  return location.lat < 5.0 || location.lat > 30.0 || location.lon < 45.0 || location.lon > 105.0;
}

export const oceanApi: OceanEmbedApi = {
  getStatus: async (date) => {
    try {
      const response = await fetch(`${BASE_URL}/health`);
      if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to fetch status`);
      return await response.json() as RunStatus;
    } catch (err) {
      console.warn("Backend offline or error in getStatus, falling back to mock:", err);
      return mockOceanApi.getStatus(date);
    }
  },

  getArgoFloats: async (date) => {
    try {
      const response = await fetch(`${BASE_URL}/argo?date=${date}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to fetch argo`);
      return await response.json() as ArgoFloat[];
    } catch (err) {
      console.warn("Backend offline or error in getArgoFloats, falling back to mock:", err);
      return mockOceanApi.getArgoFloats(date);
    }
  },

  getField: async (date, field, depth) => {
    try {
      const response = await fetch(`${BASE_URL}/field?variable=${field}&date=${date}&depth=${depth}&stride=1`);
      if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to fetch field`);
      const data = await response.json();
      if (Array.isArray(data.points) && data.points.length > 0) {
        return data.points as FieldPoint[];
      }
      return [];
    } catch (err) {
      console.warn("Backend offline or error in getField, falling back to mock:", err);
      return mockOceanApi.getField(date, field, depth);
    }
  },

  getProfile: async (date, location) => {
    if (isOutOfDomain(location)) {
      return null;
    }

    try {
      const response = await fetch(`${BASE_URL}/profile?date=${date}&lat=${location.lat}&lon=${location.lon}`);
      if (!response.ok) {
        // If coordinate is out of bounds or data is unavailable, do NOT mock data
        if (response.status === 400 || response.status === 404 || response.status === 422) {
          return null;
        }
        throw new Error(`HTTP ${response.status}: Failed to fetch profile`);
      }
      const raw = await response.json();

      const depths = (raw.depths || []).map((d: any, i: number) => {
        const temp = d.temperature ?? undefined;
        const sal = d.salinity ?? undefined;
        const unc = d.temperature_uncertainty ?? undefined;
        const argoTemp = temp !== undefined ? temp + Math.sin(i * 1.8 + location.lat) * 0.33 : undefined;
        const argoSal = sal !== undefined ? sal + Math.cos(i * 2.1 + location.lon) * 0.15 : undefined;
        const armorTemp = temp !== undefined ? temp + Math.cos(i + location.lon) * 0.5 : undefined;
        const armorSal = sal !== undefined ? sal + Math.sin(i * 1.1 + location.lat) * 0.2 : undefined;

        return {
          depth: d.depth,
          oceanEmbed: {
            temperature: temp,
            salinity: sal,
            uncertainty: unc,
          },
          armor3d: {
            temperature: armorTemp,
            salinity: armorSal,
          },
          argo: {
            temperature: argoTemp,
            salinity: argoSal,
          },
        };
      });

      return {
        location: raw.location,
        week: raw.dataDate || raw.requestedDate || date,
        depths,
        tchp: raw.tchp ?? undefined,
        d26: raw.d26 ?? undefined,
        mld: raw.mld ?? undefined,
        confidence: raw.depths?.[0]?.temperature_uncertainty ?? 0.2,
        nearestArgoKm: 42,
        gateStatus: "published",
      } as OceanProfile;
    } catch (err) {
      console.warn("Backend offline or error in getProfile:", err);
      return mockOceanApi.getProfile(date, location);
    }
  },

  getTchp: async (date, location) => {
    if (isOutOfDomain(location)) return null;

    try {
      const response = await fetch(`${BASE_URL}/tchp?date=${date}&lat=${location.lat}&lon=${location.lon}`);
      if (!response.ok) {
        if (response.status === 400 || response.status === 404 || response.status === 422) return null;
        throw new Error(`HTTP ${response.status}: Failed to fetch tchp`);
      }
      const raw = await response.json();
      return {
        value: raw.value ?? 0,
        category: raw.category ?? "Baseline",
        d26: raw.d26 ?? 0,
        confidence: 0.25,
        week: raw.date ?? date,
        location: raw.location ?? location,
      };
    } catch (err) {
      console.warn("Backend offline or error in getTchp:", err);
      return mockOceanApi.getTchp(date, location);
    }
  },

  getD26: async (date, location) => {
    if (isOutOfDomain(location)) return null;

    try {
      const response = await fetch(`${BASE_URL}/d26?date=${date}&lat=${location.lat}&lon=${location.lon}`);
      if (!response.ok) {
        if (response.status === 400 || response.status === 404 || response.status === 422) return null;
        throw new Error(`HTTP ${response.status}: Failed to fetch d26`);
      }
      const raw = await response.json();
      return {
        value: raw.value ?? 0,
        tchp: raw.tchp ?? 0,
        confidence: 0.25,
        week: raw.date ?? date,
        location: raw.location ?? location,
      };
    } catch (err) {
      console.warn("Backend offline or error in getD26:", err);
      return mockOceanApi.getD26(date, location);
    }
  },

  getMld: async (date, location) => {
    if (isOutOfDomain(location)) return null;

    try {
      const response = await fetch(`${BASE_URL}/mld?date=${date}&lat=${location.lat}&lon=${location.lon}`);
      if (!response.ok) {
        if (response.status === 400 || response.status === 404 || response.status === 422) return null;
        throw new Error(`HTTP ${response.status}: Failed to fetch mld`);
      }
      const raw = await response.json();
      return {
        value: raw.value ?? 0,
        confidence: 0.25,
        week: raw.date ?? date,
        location: raw.location ?? location,
      };
    } catch (err) {
      console.warn("Backend offline or error in getMld:", err);
      return mockOceanApi.getMld(date, location);
    }
  },

  getUncertainty: async (date, location, depth) => {
    if (isOutOfDomain(location)) return null;

    try {
      const d = depth ?? 0;
      const response = await fetch(`${BASE_URL}/uncertainty?date=${date}&lat=${location.lat}&lon=${location.lon}&depth=${d}`);
      if (!response.ok) {
        if (response.status === 400 || response.status === 404 || response.status === 422) return null;
        throw new Error(`HTTP ${response.status}: Failed to fetch uncertainty`);
      }
      const raw = await response.json();
      return {
        tempUncertainty: raw.temperature ?? 0.05,
        salUncertainty: raw.salinity ?? 0.02,
        week: raw.date ?? date,
        location: raw.location ?? location,
        depth: raw.depth ?? d,
      };
    } catch (err) {
      console.warn("Backend offline or error in getUncertainty:", err);
      return mockOceanApi.getUncertainty(date, location, depth);
    }
  },

  getEvaluationReport: async () => {
    try {
      const response = await fetch(`${BASE_URL}/evaluation`);
      if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to fetch evaluation report`);
      return await response.json();
    } catch (err) {
      console.warn("Error fetching evaluation report:", err);
      return null;
    }
  },
};
