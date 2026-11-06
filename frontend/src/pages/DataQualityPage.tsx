/** Dados e qualidade (§11.2.9): cobertura temporal, status de ingestão, lacunas. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

export function DataQualityPage() {
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: api.health });
  const coverageQuery = useQuery({
    queryKey: ["coverage"],
    queryFn: api.coverage,
  });

  const statusLine = healthQuery.data
    ? healthQuery.data.status === "ok"
      ? "API operando."
      : "Serviço de dados indisponível ou incompleto."
    : "…";

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Dados e qualidade</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="font-medium">Ambiente</h2>
          <p className="mt-2">{statusLine}</p>
          {healthQuery.data?.next_action && (
            <p className="mt-2 rounded bg-amber-50 p-3 text-amber-950">
              {healthQuery.data.next_action}
            </p>
          )}
          {healthQuery.data?.schema_revision && (
            <p className="mt-2 text-xs text-neutral-500">
              Estrutura: {healthQuery.data.schema_revision} · esperada:{" "}
              {healthQuery.data.expected_revision}
            </p>
          )}
          <p className="mt-1 text-neutral-500">
            app: {healthQuery.data?.env} · versão{" "}
            {healthQuery.data?.version || "—"} · banco:{" "}
            {healthQuery.data?.database ?? "—"}
          </p>
        </div>

        <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="font-medium">Cobertura temporal</h2>
          <p className="mt-2 text-neutral-600 dark:text-neutral-400">
            {coverageQuery.error
              ? coverageQuery.error.message
              : coverageQuery.data?.period_start
                ? `${coverageQuery.data.period_start} → ${coverageQuery.data.period_end}`
                : "Sem dados carregados (ingestão pendente)."}
          </p>
          <p className="mt-1 text-xs text-neutral-500">
            instrumentos:{" "}
            {coverageQuery.data?.instruments?.length
              ? coverageQuery.data.instruments.join(", ")
              : "—"}
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
        <h2 className="font-medium">Lotes de ingestão</h2>
        <IngestionBatches />
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white p-4 text-sm dark:border-neutral-800 dark:bg-neutral-900">
        <h2 className="font-medium">Fontes (proveniência)</h2>
        <DataSources />
      </div>
    </section>
  );
}

function IngestionBatches() {
  const q = useQuery({
    queryKey: ["ingestion-batches"],
    queryFn: () => api.ingestionBatches(20),
  });
  if (q.isLoading) return <p className="mt-2 text-neutral-500">Carregando…</p>;
  if (q.error)
    return (
      <p role="alert" className="mt-2 text-amber-700">
        {q.error.message}
      </p>
    );
  const rows = q.data ?? [];
  if (!rows.length)
    return (
      <p className="mt-2 text-neutral-500">Nenhum lote registrado ainda.</p>
    );
  return (
    <table className="mt-2 w-full text-left text-xs">
      <thead className="text-neutral-500">
        <tr>
          <th className="py-1">Fonte</th>
          <th>Dados</th>
          <th className="text-right">Total</th>
          <th className="text-right">Aceitos</th>
          <th className="text-right">Rejeit.</th>
          <th className="text-right">Duplic.</th>
          <th className="pl-3">Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((b) => (
          <tr
            key={b.id}
            className="border-t border-neutral-100 dark:border-neutral-800"
          >
            <td className="py-1">{b.source_code}</td>
            <td className="text-neutral-500">
              {b.period_start ?? "?"} → {b.period_end ?? "?"}
            </td>
            <td className="text-right tabular-nums">{b.records_total}</td>
            <td className="text-right tabular-nums">{b.records_accepted}</td>
            <td className="text-right tabular-nums">{b.records_rejected}</td>
            <td className="text-right tabular-nums">{b.records_duplicated}</td>
            <td className="pl-3">{b.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DataSources() {
  const q = useQuery({
    queryKey: ["data-sources"],
    queryFn: () => api.dataSources(),
  });
  if (q.isLoading) return <p className="mt-2 text-neutral-500">Carregando…</p>;
  if (q.error)
    return (
      <p role="alert" className="mt-2 text-amber-700">
        {q.error.message}
      </p>
    );
  const rows = q.data ?? [];
  if (!rows.length)
    return <p className="mt-2 text-neutral-500">Sem fontes registradas.</p>;
  return (
    <div className="mt-2 grid gap-2 md:grid-cols-2">
      {rows.map((s) => (
        <div
          key={s.code}
          className="rounded border border-neutral-100 p-2 text-xs dark:border-neutral-800"
        >
          <p className="font-mono font-medium">{s.code}</p>
          <p className="text-neutral-500">
            {s.satellite} · {s.product} · {s.mode}{" "}
            {s.active ? "· ativa" : "· inativa"}
          </p>
          <p className="text-neutral-500">
            detecções: {s.detections} ({s.first_seen ?? "?"} →{" "}
            {s.last_seen ?? "?"})
          </p>
        </div>
      ))}
    </div>
  );
}
