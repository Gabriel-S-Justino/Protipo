/** Anomalias mensais pré-calculadas no pipeline (honestidade: nível e nota). */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";

const LEVEL_STYLES: Record<string, string> = {
  info: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
  warning: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  alert: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

export function AnomaliesPage() {
  const q = useQuery({ queryKey: ["anomalies"], queryFn: () => api.anomalies(undefined, 100) });

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Anomalias</h1>
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        Calculadas na etapa <code>python -m pipeline anomalies</code> (z-score por mês civil vs
        baseline histórico). Sem baseline suficiente o período fica <strong>info</strong> com
        nota — nunca um alerta inflado.
      </p>

      {q.isLoading && <p className="text-sm">Carregando…</p>}
      {(q.data ?? []).length === 0 && !q.isLoading && (
        <p className="text-sm text-neutral-500">
          Nenhuma anomalia calculada ainda — rode o pipeline após o backfill preencher anos de histórico.
        </p>
      )}

      <div className="space-y-2">
        {(q.data ?? []).map((a) => (
          <div
            key={a.id}
            className="flex flex-wrap items-center gap-3 rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm dark:border-neutral-800 dark:bg-neutral-900"
          >
            <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${LEVEL_STYLES[a.level] ?? LEVEL_STYLES.info}`}>
              {a.level}
            </span>
            <span className="font-medium">{a.region ?? "global"}</span>
            <span className="text-neutral-500">{a.period[0]}</span>
            <span className="tabular-nums">obs {a.observed}</span>
            <span className="tabular-nums text-neutral-500">esp {a.expected ?? "—"}</span>
            <span className="tabular-nums text-neutral-500">z {a.score ?? "—"}</span>
            {a.notes && <span className="w-full text-xs text-neutral-500">{a.notes}</span>}
          </div>
        ))}
      </div>
    </section>
  );
}
