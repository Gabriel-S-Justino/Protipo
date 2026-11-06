import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/services/api";
import { useScope } from "@/app/Scope";
export function RegionsPage() {
  const { regionId, regions, setRegionId, name } = useScope();
  const id = regionId ?? regions.find((r) => r.level === "country")?.id;
  const q = useQuery({
    queryKey: ["region-summary", id],
    queryFn: () => api.regionSummary(id!),
    enabled: id !== undefined,
  });
  return (
    <section className="space-y-5">
      <h1 className="text-2xl font-semibold">Território brasileiro</h1>
      <p className="text-sm text-neutral-500">
        Selecione Brasil ou um dos 26 estados e Distrito Federal. Todas as
        consultas usam a mesma atividade harmonizada.
      </p>
      <div className="flex flex-wrap gap-2">
        {regions.map((r) => (
          <button
            key={r.id}
            onClick={() =>
              setRegionId(r.level === "country" ? undefined : r.id)
            }
            className={`rounded-lg border px-3 py-2 text-sm ${r.id === id ? "border-orange-500 bg-orange-50 text-orange-900" : "dark:border-neutral-700"}`}
          >
            {r.name}
          </button>
        ))}
      </div>
      <h2 className="font-semibold">{name}</h2>
      {q.isLoading && <p>Carregando resumo…</p>}
      {q.error && <p role="alert">{q.error.message}</p>}
      {q.data && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              ["Atividade VIIRS equivalente", q.data.totals.total],
              ["Últimos 30 dias", q.data.totals.last_30d],
              ["Dias com atividade", q.data.totals.active_days],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-xl border p-4 dark:border-neutral-800"
              >
                <p className="text-xs text-neutral-500">{label}</p>
                <p className="mt-1 text-2xl">
                  {Number(value).toLocaleString("pt-BR", {
                    maximumFractionDigits: 1,
                  })}
                </p>
              </div>
            ))}
          </div>
          <div className="h-80 rounded-xl border p-4 dark:border-neutral-800">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={q.data.monthly_recent}>
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar
                  dataKey="total"
                  name="Atividade VIIRS equivalente"
                  fill="#ea580c"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-neutral-500">
            {q.data.note} Unidade: {q.data.unit}.
          </p>
        </>
      )}
    </section>
  );
}
