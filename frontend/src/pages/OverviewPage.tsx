/** Visão geral (§11.2.1): totais, últimos 30 dias vs histórico, cobertura e qualidade. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-1 text-xs text-neutral-500">{hint}</div>}
    </div>
  );
}

export function OverviewPage() {
  const summaryQuery = useQuery({ queryKey: ["dashboard-summary"], queryFn: api.dashboardSummary });
  const coverageQuery = useQuery({ queryKey: ["coverage"], queryFn: api.coverage });

  if (summaryQuery.isLoading || coverageQuery.isLoading) {
    return <div aria-live="polite" className="text-sm text-neutral-500">Carregando…</div>;
  }

  if (summaryQuery.error || coverageQuery.error) {
    const status = ((summaryQuery.error ?? coverageQuery.error) as { status?: number }).status;
    return (
      <div role="alert" className="max-w-prose rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-700 dark:bg-amber-950">
        <p className="font-medium">Dados reais indisponíveis.</p>
        <p className="mt-1 text-neutral-700 dark:text-neutral-300">
          {status === 503
            ? "Configure o banco (DATABASE_URL) e carregue dados via pipeline (docs/SETUP.md). Sem banco, não apresentamos números."
            : "Não foi possível consultar a API. Verifique o backend e tente novamente."}
        </p>
      </div>
    );
  }

  const s = summaryQuery.data!;
  const c = coverageQuery.data!;

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Visão geral</h1>
      <p className="max-w-prose text-sm text-neutral-600 dark:text-neutral-400">{s.unified_series_note}</p>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Focos (série unificada)" value={s.total.toLocaleString("pt-BR")} />
        <Stat label="Últimos 30 dias (real)" value={s.last_30d.toLocaleString("pt-BR")} />
        <Stat
          label="Média diária histórica (12 m)"
          value={s.last_30d_avg_hist == null ? "—" : s.last_30d_avg_hist.toFixed(1)}
          hint="Referência para comparar o período recente"
        />
        <Stat
          label="Parcela harmonizada"
          value={c.harmonized_share == null ? "—" : `${(c.harmonized_share * 100).toFixed(1)}%`}
          hint="Fração MODIS da série na escala VIIRS"
        />
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
        <h2 className="font-medium">Cobertura de dados</h2>
        <p className="mt-2 text-neutral-600 dark:text-neutral-400">
          {c.period_start && c.period_end
            ? `${c.period_start} → ${c.period_end} · instrumentos: ${c.instruments.join(", ")}`
            : "Nenhum dado real carregado — ingere a série via pipeline (fetch/backfill → ingest)."}
        </p>
      </div>
    </section>
  );
}
