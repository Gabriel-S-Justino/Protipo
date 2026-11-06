/** Regiões: ranking real + resumo do Ceará (totals, mensal, top células 0.25°). */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "@/services/api";

export function RegionsPage() {
  const [selected, setSelected] = useState<number>(1);
  const regionsQuery = useQuery({ queryKey: ["regions"], queryFn: () => api.regions(50) });
  const summaryQuery = useQuery({
    queryKey: ["region-summary", selected],
    queryFn: () => api.regionSummary(selected),
  });

  return (
    <section className="space-y-6">
      <h1 className="text-xl font-semibold">Regiões</h1>

      <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white text-sm dark:border-neutral-800 dark:bg-neutral-900">
        <table className="w-full text-left">
          <thead className="bg-neutral-100 text-xs uppercase tracking-wide text-neutral-500 dark:bg-neutral-800">
            <tr>
              <th className="px-3 py-2">Nome</th>
              <th className="px-3 py-2">Nível</th>
              <th className="px-3 py-2">Total</th>
              <th className="px-3 py-2">Últ. 30 d</th>
              <th className="px-3 py-2">Instrumentos</th>
              <th className="px-3 py-2">DEMO</th>
            </tr>
          </thead>
          <tbody>
            {(regionsQuery.data ?? []).map((r) => (
              <tr
                key={r.id}
                onClick={() => setSelected(r.id)}
                className={`cursor-pointer border-t border-neutral-200 dark:border-neutral-800 ${
                  r.id === selected ? "bg-orange-50 dark:bg-orange-950/40" : ""
                }`}
              >
                <td className="px-3 py-2 font-medium">{r.name}</td>
                <td className="px-3 py-2 text-neutral-500">{r.level}</td>
                <td className="px-3 py-2">{r.total}</td>
                <td className="px-3 py-2">{r.last_30d}</td>
                <td className="px-3 py-2 text-neutral-500">{r.instruments.join(", ") || "—"}</td>
                <td className="px-3 py-2">{r.is_demo ? "sim" : "não"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {summaryQuery.data && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-5 text-sm">
            {[
              ["Total (não-DEMO)", summaryQuery.data.totals.total],
              ["MODIS", summaryQuery.data.totals.modis_count],
              ["VIIRS", summaryQuery.data.totals.viirs_count],
              ["Últ. 30 d", summaryQuery.data.totals.last_30d],
              ["Dias ativos", summaryQuery.data.totals.active_days],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
                <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
                <p className="mt-1 text-2xl font-semibold">{value as number}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
            <h2 className="mb-3 text-sm font-medium">Mensal (últimos 36 meses, reais)</h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={summaryQuery.data.monthly_recent}>
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="total" name="VIIRS" stackId="a" fill="#38bdf8" />
                  <Bar dataKey="modis_count" name="MODIS" stackId="a" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-neutral-500">{summaryQuery.data.note}</p>
          </div>

          {summaryQuery.data.top_grid_cells.length > 0 && (
            <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
              <h2 className="mb-3 text-sm font-medium">Top células 0,25° (proxy até a malha IBGE)</h2>
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-wide text-neutral-500">
                  <tr>
                    <th className="py-1 text-left">Lat</th>
                    <th className="py-1 text-left">Lon</th>
                    <th className="py-1 text-right">Total</th>
                    <th className="py-1 text-right">Noturnos</th>
                  </tr>
                </thead>
                <tbody>
                  {summaryQuery.data.top_grid_cells.map((c, i) => (
                    <tr key={i} className="border-t border-neutral-100 dark:border-neutral-800">
                      <td className="py-1">{c.lat_center}</td>
                      <td className="py-1">{c.lon_center}</td>
                      <td className="py-1 text-right">{c.total}</td>
                      <td className="py-1 text-right">{c.night_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
