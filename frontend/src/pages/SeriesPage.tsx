import { useQuery } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/services/api";
import { useScope } from "@/app/Scope";
export function SeriesPage() {
  const { regionId, name } = useScope();
  const q = useQuery({
    queryKey: ["unified-series", regionId],
    queryFn: () => api.unifiedSeries(regionId),
  });
  return (
    <section className="space-y-5">
      <h1 className="text-2xl font-semibold">Histórico unificado · {name}</h1>
      <p className="max-w-3xl text-sm text-neutral-500">
        Uma única curva na escala VIIRS. Os dados MODIS entram após conversão
        calibrada por área; os sensores não são somados.
      </p>
      {q.isLoading && <p role="status">Carregando série…</p>}
      {q.error && <p role="alert">{q.error.message}</p>}
      {q.data && !q.data.points.length && (
        <p>Histórico ainda não processado para esta área.</p>
      )}
      {!!q.data?.points.length && (
        <div className="rounded-xl border bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={q.data.points}>
                <XAxis dataKey="period_start" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area
                  dataKey="value_viirs"
                  name="Atividade equivalente VIIRS"
                  stroke="#ea580c"
                  fill="#fdba74"
                  connectNulls={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-neutral-500">
            {q.data.unit}. Totais podem ser parciais onde houver lacunas de
            cobertura.
          </p>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-neutral-500">
            <th>Período</th>
            <th>Atividade equivalente VIIRS</th>
            <th>Cobertura dos dias nas áreas ativas</th>
          </tr>
        </thead>
        <tbody>
          {q.data?.points.map((p) => (
            <tr
              key={p.period_start}
              className="border-t dark:border-neutral-800"
            >
              <td className="py-2">{p.period_start}</td>
              <td>
                {p.value_viirs.toLocaleString("pt-BR", {
                  maximumFractionDigits: 1,
                })}
              </td>
              <td>
                {Math.round(100 * p.coverage_fraction)}%
                {p.coverage_fraction < 1 ? " · parcial" : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
