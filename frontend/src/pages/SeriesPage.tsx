/** Séries históricas (§11.2.6): série unificada com incerteza e proveniência. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export function SeriesPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["unified-series"], queryFn: () => api.unifiedSeries() });

  if (isLoading) return <div aria-live="polite" className="text-sm text-neutral-500">Carregando…</div>;
  if (error) {
    return (
      <div role="alert" className="max-w-prose rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-700 dark:bg-amber-950">
        Séries indisponíveis: alimente harmonized_series pelo pipeline (harmonize, fase 4).
      </div>
    );
  }

  const points = data!.points;
  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Séries históricas (escala VIIRS)</h1>
      <p className="max-w-prose text-sm text-neutral-600 dark:text-neutral-400">{data!.provenance}</p>

      {points.length === 0 ? (
        <p className="text-sm text-neutral-500">Nenhum dado ainda: execute o pipeline (ingest → harmonize).</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <th className="pb-2">Período</th>
              <th className="pb-2">Bruto</th>
              <th className="pb-2">VIIRS-equivalente</th>
              <th className="pb-2">IC 95%</th>
              <th className="pb-2">Fonte</th>
              <th className="pb-2">Qualidade</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.period_start} className="border-t border-neutral-200 dark:border-neutral-800">
                <td className="py-1">{p.period_start}</td>
                <td>{p.value_raw.toFixed(0)}</td>
                <td className="font-medium">{p.value_viirs.toFixed(1)}</td>
                <td className="text-neutral-500">
                  {p.ci_low == null || p.ci_high == null ? "—" : `[${p.ci_low.toFixed(1)}, ${p.ci_high.toFixed(1)}]`}
                </td>
                <td className="text-xs">{p.source === "viirs_raw" ? "VIIRS direto" : "MODIS harmonizado"}</td>
                <td className="text-xs">{p.quality}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
