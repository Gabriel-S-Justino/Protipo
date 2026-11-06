import type * as GeoJSON from "geojson";
const BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
    /\/$/,
    "",
  ) ?? "";
export type Region = {
  id: number;
  name: string;
  level: string;
  geocode: string;
  bbox_w: number;
  bbox_s: number;
  bbox_e: number;
  bbox_n: number;
};
export type Health = {
  status: "ok" | "degraded";
  app: string;
  env: string;
  database: string | null;
  version: string;
  readiness?: string;
  schema_revision?: string | null;
  expected_revision?: string | null;
  next_action?: string | null;
};
export type Coverage = {
  period_start: string | null;
  period_end: string | null;
  instruments: string[];
  harmonized_share: number | null;
  covered_days: number;
};
export type DashboardSummary = {
  total: number;
  last_30d: number;
  last_30d_avg_hist: number | null;
  unified_series_note: string;
  unit: string;
  region: string;
};
export type CalendarCell = {
  cell_id: number;
  cell_key: string;
  lat: number;
  lon: number;
  state: string | null;
  period_of_year: number;
  probability: number;
  ci_low: number;
  ci_high: number;
  years_used: number;
  expected_count: number;
  confidence: string;
  validation: {
    brier_score: number | null;
    test_years: number;
    method: string;
  };
  calculated_at: string;
};
export type HeatProperties = Partial<CalendarCell> & {
  weight?: number;
  first_date?: string;
  last_date?: string;
};
export type HeatData = GeoJSON.FeatureCollection<
  GeoJSON.Point,
  HeatProperties
> & { metadata?: { unit?: string; meaning?: string; region?: string } };
export type UnifiedSeries = {
  unit: string;
  region: string;
  provenance: string;
  points: {
    period_start: string;
    value_viirs: number;
    coverage_fraction: number;
    quality: string;
  }[];
};
export type RegionSummary = {
  region: Region;
  totals: {
    total: number;
    last_30d: number;
    active_days: number;
    period_start: string | null;
    period_end: string | null;
  };
  monthly_recent: { month: string; total: number }[];
  note: string;
  unit: string;
};
export type Anomaly = {
  id: number;
  region: string | null;
  period: [string, string];
  observed: number;
  expected: number | null;
  score: number | null;
  level: string;
  notes: string | null;
};
export type IngestionBatch = {
  id: number;
  source_code: string;
  period_start: string | null;
  period_end: string | null;
  records_total: number;
  records_accepted: number;
  records_rejected: number;
  records_duplicated: number;
  status: string;
  pipeline_version: string;
  created_at: string;
};
export type DataSourceInfo = {
  code: string;
  sensor: string;
  satellite: string;
  product: string;
  mode: string;
  active: boolean;
  detections: number;
  first_seen: string | null;
  last_seen: string | null;
};
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function getJson<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
): Promise<T> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params))
    if (value !== undefined && value !== "") search.set(key, String(value));
  const response = await fetch(BASE + path + (search.size ? "?" + search : ""));
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? "Erro da API");
  }
  return response.json() as Promise<T>;
}
export const api = {
  health: () => getJson<Health>("/api/health"),
  dashboardSummary: (region_id?: number) =>
    getJson<DashboardSummary>("/api/dashboard/summary", { region_id }),
  coverage: () => getJson<Coverage>("/api/metadata/coverage"),
  regions: (limit = 100) => getJson<Region[]>("/api/regions", { limit }),
  regionSummary: (id: number) =>
    getJson<RegionSummary>(`/api/regions/${id}/summary`),
  calendar: (period_type: "week" | "month", region_id?: number) =>
    getJson<CalendarCell[]>("/api/calendar/probability", {
      period_type,
      region_id,
    }),
  locations: (
    period_type: "week" | "month",
    period: number,
    region_id?: number,
  ) =>
    getJson<HeatData>("/api/calendar/locations", {
      period_type,
      period,
      region_id,
    }),
  heat: (region_id?: number, from?: string, to?: string) =>
    getJson<HeatData>("/api/map/heat", { region_id, from, to }),
  unifiedSeries: (region_id?: number) =>
    getJson<UnifiedSeries>("/api/series/unified", { region_id }),
  anomalies: (region_id?: number, limit = 100) =>
    getJson<Anomaly[]>("/api/analytics/anomalies", { region_id, limit }),
  ingestionBatches: (limit = 30) =>
    getJson<IngestionBatch[]>("/api/ingestion/batches", { limit }),
  dataSources: () => getJson<DataSourceInfo[]>("/api/metadata/sources"),
};
