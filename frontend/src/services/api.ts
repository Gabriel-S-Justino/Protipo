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
};
