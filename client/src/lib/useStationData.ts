import { useEffect, useState } from "react";

export const VARIABLE_META: Record<string, { label: string; unit: string; color: string }> = {
  NEE: { label: "Net ecosystem exchange", unit: "gC m⁻² d⁻¹", color: "#2F6B3B" },
  GPP: { label: "Gross primary production", unit: "gC m⁻² d⁻¹", color: "#6B8F3A" },
  LE: { label: "Latent heat flux", unit: "W m⁻²", color: "#2C7DA0" },
  H: { label: "Sensible heat flux", unit: "W m⁻²", color: "#C78C1B" },
  TA: { label: "Air temperature", unit: "°C", color: "#9D3D2C" },
  SW_IN: { label: "Incoming shortwave", unit: "W m⁻²", color: "#B5651D" },
};

export const BIOME_COLORS: Record<string, string> = {
  "Evergreen Broadleaf Forest": "#2F6B3B",
  "Evergreen Needleleaf Forest": "#1B5E3A",
  "Deciduous Broadleaf Forest": "#6B8F3A",
  "Mixed Forest": "#4A7C59",
  Wetland: "#2C7DA0",
  Grassland: "#C78C1B",
  Savanna: "#B5651D",
  Cropland: "#9D7E2C",
  Unknown: "#7A7A7A",
};

export function biomeColor(biome: string): string {
  return BIOME_COLORS[biome] ?? "#7A7A7A";
}

// Data shapes mirror the JSON emitted by scripts_export_web_data.py.
export type ValidPct = Record<string, number>;

export interface StationJson {
  siteId: string;
  siteName: string;
  country: string;
  regionalScope: string;
  ecosystem: string;
  ecosystemBiome: string;
  igbp: string;
  network: string;
  lat: number;
  lon: number;
  yearStart: number;
  yearEnd: number;
  coverageYears: number;
  observations: number;
  utilityScore: number;
  qualityClass: string;
  qualityColor: string;
  markerRadius: number;
  validPct: ValidPct;
  acceptableQcPct: number;
  variablesAvailableCount: number;
}

export interface ReachInfo {
  siteId: string;
  biome: string;
  igbp: string;
  stationsSharingBiome: number;
  soleRepresentative: boolean;
  lat: number;
  lon: number;
  nearestNeighborId: string | null;
  nearestNeighborKm: number | null;
  reachRadiusKm: number | null;
}

export interface Representativeness {
  biomeCoverage: { biome: string; stationCount: number }[];
  perStation: ReachInfo[];
}

export interface StationsPayload {
  stations: StationJson[];
  representativeness: Representativeness;
}

export interface VarStats {
  n: number | null;
  mean: number | null;
  sd: number | null;
  min: number | null;
  p5: number | null;
  p25: number | null;
  median: number | null;
  p75: number | null;
  p95: number | null;
  max: number | null;
}

export interface StatsPayload {
  variables: string[];
  perStation: {
    siteId: string;
    variables: Record<string, VarStats>;
    monthlyClimatology: Record<string, (number | null)[]>;
  }[];
}

export interface TimeseriesPayload {
  siteId: string;
  variables: string[];
  daily: Record<string, number | string | null>[];
}

// Rigorous environmental representativeness (scripts_representativeness_analysis.py).
export interface RepresentativenessGrid {
  method: string;
  source: string;
  synthetic: boolean;
  variables: { id: string; label: string }[];
  bbox: { lon_min: number; lon_max: number; lat_min: number; lat_max: number };
  resolutionDeg: number;
  thresholdSd: number;
  coverageFraction: number;
  regionAreaKm2: number;
  nStations: number;
  nValidCells: number;
  grid: {
    latStart: number;
    lonStart: number;
    dLat: number;
    dLon: number;
    nLat: number;
    nLon: number;
    rep: (number | null)[];
  };
  perStation: {
    siteId: string;
    biome: string;
    representativeAreaKm2: number;
    representativeAreaPct: number;
    assignedAreaKm2: number;
    medianDissimilarity: number;
  }[];
}

function dataUrl(path: string): string {
  // import.meta.env.BASE_URL ends with "/" (e.g. "/eddy-patagonia-chile/").
  return `${import.meta.env.BASE_URL}data/${path}`;
}

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function useJson<T>(path: string | null): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null });
  useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    fetch(dataUrl(path))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: T) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [path]);
  return state;
}

export function useStations() {
  return useJson<StationsPayload>("stations.json");
}

export function useStats() {
  return useJson<StatsPayload>("stats.json");
}

export function useTimeseries(siteId: string | null) {
  return useJson<TimeseriesPayload>(siteId ? `timeseries/${siteId}.json` : null);
}

// Optional: only present once the representativeness analysis has been run.
// A missing file resolves to an error/null state and the UI degrades gracefully.
export function useRepresentativenessGrid() {
  return useJson<RepresentativenessGrid>("representativeness_grid.json");
}

/** Diverging score → colour ramp (red = poorly represented, green = well). */
export function representativenessColor(score: number): string {
  const t = Math.max(0, Math.min(1, score));
  // Interpolate copper/red (#9D3D2C) → amber (#C78C1B) → forest (#2F6B3B).
  const stops: [number, [number, number, number]][] = [
    [0, [157, 61, 44]],
    [0.5, [199, 140, 27]],
    [1, [47, 107, 59]],
  ];
  let lo = stops[0];
  let hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (t >= stops[i][0] && t <= stops[i + 1][0]) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const span = hi[0] - lo[0] || 1;
  const f = (t - lo[0]) / span;
  const c = lo[1].map((v, k) => Math.round(v + (hi[1][k] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}
