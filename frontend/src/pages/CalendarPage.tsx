/** Calendário de probabilidade (§11.2.5): mapa de calor semana × prob. com intervalo. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

/** Página 100% lida de calendar_probabilities (pré-calculada pelo pipeline).
 *  "Probabilidade histórica", NUNCA previsão de incêndio. */

const WEEKS = Array.from({ length: 53 }, (_, i) => i + 1);

function colorFor(p: number | null): string {
  if (p == null) return "bg-neutral-200 dark:bg-neutral-800";
  const pct = Math.round(p * 100);
  if (pct < 10) return "bg-emerald-200 dark:bg-emerald-900";
  if (pct < 30) return "bg-yellow-200 dark:bg-yellow-900";
  if (pct < 60) return "bg-orange-300 dark:bg-orange-900";
  return "bg-red-400 dark:bg-red-900";
}

export function CalendarPage() {
  const { data: cells, isLoading, error } = useQuery({ queryKey: ["calendar-week"], queryFn: () => api.calendar("week") });

  if (isLoading) return <div aria-live="polite" className="text-sm text-neutral-500">Carregando…</div>;
  if (error) {
    return (
      <div role="alert" className="max-w-prose rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-700 dark:bg-amber-950">
        Calendário indisponível: é o pipeline que precalcula <code>calendar_probabilities</code>
        {" "}(comando <code>calendar</code>, fase 5). Configure o banco e o pipeline.
      </div>
    );
  }

  const byWeek = new Map(cells!.map((c) => [c.period_of_year, c]));

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Calendário de probabilidade (histórica)</h1>
      <p className="max-w-prose text-sm text-neutral-600 dark:text-neutral-400">
        Probabilidade de ≥ 1 foco (escala VIIRS) na região por semana do ano, com intervalo de confiança
        e nº de anos usados. Estatística histórica calibrada — não é previsão de incêndio.
        Fonte: NASA FIRMS (MODIS/VIIRS, série unificada).
      </p>

      {cells!.length === 0 ? (
        <p className="text-sm text-neutral-500">
          Sem resultados pré-calculados (pipeline ainda não foi executado). A tabela abaixo mostra as 53
          semanas como "dados insuficientes" — nunca números inventados.
        </p>
      ) : null}

      <div className="overflow-x-auto">
        <table className="w-full text-xs" data-testid="calendar-heatmap">
          <thead>
            <tr>
              {WEEKS.map((w) => (
                <th key={w} className="px-1 pb-1 font-normal text-neutral-500">{w}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {WEEKS.map((w) => {
                const cell = byWeek.get(w);
                return (
                  <td key={w} className="p-0.5">
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded ${colorFor(cell?.probability ?? null)}`}
                      title={
                        cell
                          ? `P=${(cell.probability * 100).toFixed(0)}% · IC=[${((cell.ci_low ?? 0) * 100).toFixed(0)}%, ${((cell.ci_high ?? 100) * 100).toFixed(0)}%] · anos: ${cell.years_used} · conf.: ${cell.confidence}`
                          : "dados insuficientes"
                      }
                    >
                      {cell ? (cell.probability * 100).toFixed(0) : "–"}
                    </div>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-xs text-neutral-500">
        Legenda: verde &lt; 10% · amarelo 10–29% · laranja 30–59% · vermelho ≥ 60% · "–" = dados insuficientes.
      </p>
    </section>
  );
}
