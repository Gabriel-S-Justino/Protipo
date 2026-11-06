/** Cliente HTTP para a API FastAPI (/api/*). Em dev, o proxy do Vite encaminha. */

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export type Health = { status: "ok" | "degraded"; app: string; env: string; database: string | null; version: string };
export type DashboardSummary = { total: number; last_30d: number; last_30d_avg_hist: number | null; unified_series_note: string };
export type Coverage = { period_start: string | null; period_end: string | null; instruments: string[]; harmonized_share: number | null };
export type CalendarCell = {
  period_of_year: number;
  probability: number;
  ci_low: number | null;
  ci_high: number | null;
  years_used: number;
  expected_count: number | null;
  harmonized_share: number | null;
  confidence: string;
};
export type UnifiedSeriesPoint = {
  period_start: string;
  value_raw: number;
  value_viirs: number;
  ci_low: number | null;
  ci_high: number | null;
  source: "viirs_raw" | "modis_harmonized";
  quality: string;
  method: string | null;
};
export type UnifiedSeries = { unit: string; provenance: string; points: UnifiedSeriesPoint[] };

export type Region = {
  id: number;
  level: string;
  name: string;
  geocode: string | null;
  is_demo: boolean;
  total: number;
  last_30d: number;
  instruments: string[];
};
export type RegionSummary = {
  region: { id: number; level: string; name: string; geocode: string | null; is_demo: boolean };
  totals: {
    total: number;
    modis_count: number;
    viirs_count: number;
    last_30d: number;
    night_count: number;
    active_days: number;
    period_start: string | null;
    period_end: string | null;
  };
  monthly_recent: { month: string; total: number; modis_count: number }[];
  top_grid_cells: { lat_center: number; lon_center: number; total: number; night_count: number }[];
  note: string;
};
export type Anomaly = {
  id: number;
  region: string | null;
  period: [string, string];
  observed: number;
  expected: number | null;
  score: number | null;
  level: string;
  method: string;
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
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, { headers: { Accept: "application/json" } });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new ApiError(resp.status, (body as { detail?: string }).detail ?? "Erro da API");
  }
  return (await resp.json()) as T;
}

export const api = {
  health: () => getJson<Health>("/api/health"),
  dashboardSummary: () => getJson<DashboardSummary>("/api/dashboard/summary"),
  coverage: () => getJson<Coverage>("/api/metadata/coverage"),
  calendar: (periodType: "day" | "week" | "month" = "week") =>
    getJson<CalendarCell[]>(`/api/calendar/probability?period_type=${periodType}`),
  unifiedSeries: (limit = 240) => getJson<UnifiedSeries>(`/api/series/unified?limit=${limit}`),
  regions: (limit = 50) => getJson<Region[]>(`/api/regions?limit=${limit}`),
  regionSummary: (id: number) => getJson<RegionSummary>(`/api/regions/${id}/summary`),
  anomalies: (regionId?: number, limit = 100) =>
    getJson<Anomaly[]>(
      `/api/analytics/anomalies?limit=${limit}${regionId ? `&region_id=${regionId}` : ""}`,
    ),
  ingestionBatches: (limit = 30) => getJson<IngestionBatch[]>(`/api/ingestion/batches?limit=${limit}`),
  dataSources: () => getJson<DataSourceInfo[]>("/api/metadata/sources"),
};
