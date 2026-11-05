/** Dados e qualidade (§11.2.9): cobertura temporal, status de ingestão, lacunas. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export function DataQualityPage() {
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: api.health });
  const coverageQuery = useQuery({ queryKey: ["coverage"], queryFn: api.coverage });

  const statusLine = healthQuery.data
    ? healthQuery.data.status === "ok"
      ? "API operando."
      : "API degradada (banco ausente)."
    : "…";

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Dados e qualidade</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="font-medium">Ambiente</h2>
          <p className="mt-2">{statusLine}</p>
          <p className="mt-1 text-neutral-500">
            app: {healthQuery.data?.env} · versão {healthQuery.data?.version || "—"} · banco: {healthQuery.data?.database ?? "—"}
          </p>
        </div>

        <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="font-medium">Cobertura temporal</h2>
          <p className="mt-2 text-neutral-600 dark:text-neutral-400">
            {coverageQuery.data?.period_start
              ? `${coverageQuery.data.period_start} → ${coverageQuery.data.period_end}`
              : "Sem dados carregados (ingestão pendente)."}
          </p>
          <p className="mt-1 text-xs text-neutral-500">
            instrumentos: {coverageQuery.data?.instruments?.length ? coverageQuery.data.instruments.join(", ") : "—"}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
        <h2 className="font-medium">Status das ingestões</h2>
        <p className="mt-2 text-neutral-600 dark:text-neutral-400">
          Relatórios por lote (fonte, sensor, totais, rejeitados, duplicados, erros) em <code>GET /api/ingestion/batches</code> —
          fase 3 do plano; o comando <code>python -m pipeline report</code> já lista os lotes recentes.
        </p>
      </div>
    </section>
  );
}
