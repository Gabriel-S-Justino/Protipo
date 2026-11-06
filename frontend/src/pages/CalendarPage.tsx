import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CalendarCell } from "@/services/api";
import { useScope } from "@/app/Scope";
import { FireMapView } from "./FireMapView";
const MONTHS = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];
const pct = (v: number) => `${(100 * v).toFixed(0)}%`;
function isoWeek(d: Date) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  return Math.ceil(
    ((t.getTime() - Date.UTC(t.getUTCFullYear(), 0, 1)) / 86400000 + 1) / 7,
  );
}
function range(year: number, period: number, kind: "week" | "month") {
  if (kind === "month") return `${MONTHS[period - 1]} de ${year}`;
  const d = new Date(Date.UTC(year, 0, 4));
  d.setUTCDate(d.getUTCDate() + 1 - (d.getUTCDay() || 7) + (period - 1) * 7);
  const end = new Date(d.getTime() + 6 * 86400000);
  const fmt = (v: Date) => v.toLocaleDateString("pt-BR", { timeZone: "UTC" });
  return `${fmt(d)} a ${fmt(end)}`;
}
function cellColor(value: number) {
  return value < 0.1
    ? "#fff7d6"
    : value < 0.3
      ? "#fee08b"
      : value < 0.6
        ? "#fdae61"
        : value < 0.8
          ? "#f46d43"
          : "#a50026";
}
export function CalendarPage() {
  const { regionId, name, bbox } = useScope();
  const now = new Date();
  const [kind, setKind] = useState<"week" | "month">("week");
  const [year, setYear] = useState(now.getFullYear());
  const [period, setPeriod] = useState(isoWeek(now));
  const [selected, setSelected] = useState<number>();
  useEffect(() => setSelected(undefined), [regionId, kind]);
  const count = kind === "month" ? 12 : isoWeek(new Date(year, 11, 28));
  useEffect(() => {
    if (period > count) setPeriod(count);
  }, [period, count]);
  const q = useQuery({
    queryKey: ["calendar", kind, regionId],
    queryFn: () => api.calendar(kind, regionId),
  });
  const locations = useQuery({
    queryKey: ["locations", kind, period, regionId],
    queryFn: () => api.locations(kind, period, regionId),
  });
  const cells = new Map<number, CalendarCell[]>();
  for (const cell of q.data ?? [])
    cells.set(cell.cell_id, [...(cells.get(cell.cell_id) ?? []), cell]);
  const ranked = (locations.data?.features ?? [])
    .map((f) => f.properties as CalendarCell)
    .sort(
      (a, b) =>
        b.probability - a.probability || b.expected_count - a.expected_count,
    );
  const focus = ranked.find((c) => c.cell_id === selected);
  return (
    <section className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Quando e onde · {name}</h1>
        <p className="mt-2 max-w-3xl text-sm text-neutral-600 dark:text-neutral-400">
          Probabilidade histórica de uma área apresentar atividade de calor na
          semana ou no mês escolhido. Use a recorrência para planejamento: as
          condições meteorológicas futuras podem mudar o resultado.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-4 rounded-xl border bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
        <label className="text-sm">
          Agrupar por{" "}
          <select
            aria-label="Agrupar calendário"
            value={kind}
            onChange={(e) => {
              const k = e.target.value as "week" | "month";
              setKind(k);
              setPeriod(k === "month" ? now.getMonth() + 1 : isoWeek(now));
            }}
            className="ml-2 rounded border bg-transparent p-2"
          >
            <option value="week">Semana</option>
            <option value="month">Mês</option>
          </select>
        </label>
        <label className="text-sm">
          Ano de planejamento{" "}
          <select
            aria-label="Ano de planejamento"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="ml-2 rounded border bg-transparent p-2"
          >
            {[now.getFullYear(), now.getFullYear() + 1].map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Período{" "}
          <select
            aria-label="Período do calendário"
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="ml-2 rounded border bg-transparent p-2"
          >
            {Array.from({ length: count }, (_, i) => i + 1).map((p) => (
              <option key={p} value={p}>
                {kind === "month" ? MONTHS[p - 1] : `Semana ${p}`}
              </option>
            ))}
          </select>
        </label>
        <p className="text-sm font-medium text-orange-700 dark:text-orange-300">
          {range(year, period, kind)}
        </p>
      </div>
      <p className="text-xs text-neutral-500">
        O ano organiza as datas; a estimativa usa os anos históricos completos
        disponíveis, sem incorporar previsão de chuva, vento ou seca.
      </p>
      {(q.isFetching || locations.isFetching) && (
        <p role="status">Atualizando calendário…</p>
      )}
      {(q.error || locations.error) && (
        <p
          role="alert"
          className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"
        >
          {(q.error ?? locations.error)?.message}
        </p>
      )}
      {locations.data && !ranked.length && (
        <p className="rounded border p-4 text-sm">
          Dados insuficientes para este período. São necessários pelo menos 3
          anos com cobertura completa por área. Ausência de estimativa não
          significa risco zero.
        </p>
      )}
      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <FireMapView
          mode="flat"
          regionBbox={bbox}
          data={locations.data}
          probability
          selectedCell={selected}
          onCellSelect={setSelected}
        />
        <aside className="space-y-3 rounded-xl border bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="font-semibold">Áreas com maior recorrência</h2>
          <p className="text-xs text-neutral-500">
            Ordenadas por probabilidade e atividade esperada. Cada área tem
            cerca de 50 km; selecione para localizar.
          </p>
          {ranked.slice(0, 8).map((c, i) => (
            <button
              key={c.cell_id}
              onClick={() => setSelected(c.cell_id)}
              className="block w-full rounded-lg border border-neutral-200 p-3 text-left hover:border-orange-500 dark:border-neutral-700"
            >
              <span className="flex justify-between text-sm font-medium">
                <span>
                  {i + 1}. {c.state ?? "Área brasileira"}
                </span>
                <span>{pct(c.probability)}</span>
              </span>
              <span className="mt-1 block text-xs text-neutral-500">
                {c.lat.toFixed(2)}°, {c.lon.toFixed(2)}° · {c.years_used} anos ·
                IC {pct(c.ci_low)}–{pct(c.ci_high)}
              </span>
            </button>
          ))}
          {focus && (
            <div className="rounded-lg bg-orange-50 p-3 text-sm text-orange-950">
              <strong>Área selecionada</strong>
              <p>
                {pct(focus.probability)} de recorrência · incerteza{" "}
                {pct(focus.ci_low)}–{pct(focus.ci_high)}.
              </p>
              <p className="mt-2 text-xs">
                {focus.validation.brier_score == null
                  ? "Validação temporal ainda sem anos suficientes."
                  : `Brier ${focus.validation.brier_score.toFixed(3)} em ${focus.validation.test_years} anos de teste (menor é melhor; não garante previsão futura).`}
              </p>
            </div>
          )}
        </aside>
      </div>
      <div className="rounded-xl border bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
        <h2 className="font-semibold">Calendário por localização</h2>
        <p className="mb-3 mt-1 text-xs text-neutral-500">
          Até 20 áreas com maior atividade esperada. Cinza = sem estimativa.
          Clique em uma célula para selecionar o período e localizar a área.
        </p>
        <div className="overflow-x-auto">
          <table
            className="w-full border-separate border-spacing-1 text-xs"
            aria-label="Calendário de recorrência por área"
          >
            <thead>
              <tr>
                <th className="sticky left-0 bg-white p-2 text-left dark:bg-neutral-900">
                  Localização
                </th>
                {Array.from({ length: count }, (_, i) => (
                  <th key={i} className="min-w-10">
                    {kind === "month" ? MONTHS[i].slice(0, 3) : i + 1}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...cells.entries()].map(([id, values]) => (
                <tr key={id}>
                  <th className="sticky left-0 whitespace-nowrap bg-white p-2 text-left font-normal dark:bg-neutral-900">
                    {values[0].state ?? "Brasil"}
                    <span className="block text-neutral-500">
                      {values[0].lat.toFixed(2)}°, {values[0].lon.toFixed(2)}°
                    </span>
                  </th>
                  {Array.from({ length: count }, (_, i) => {
                    const c = values.find((v) => v.period_of_year === i + 1);
                    return (
                      <td key={i}>
                        <button
                          onClick={() => {
                            setPeriod(i + 1);
                            setSelected(id);
                          }}
                          aria-label={`${values[0].state ?? "Brasil"}, ${kind === "week" ? "semana" : "mês"} ${i + 1}: ${c ? pct(c.probability) : "dados insuficientes"}`}
                          title={
                            c
                              ? `${pct(c.probability)} · IC ${pct(c.ci_low)}–${pct(c.ci_high)} · ${c.years_used} anos`
                              : "Dados insuficientes"
                          }
                          className="h-10 w-full min-w-10 rounded text-neutral-950 focus:outline focus:outline-2 focus:outline-orange-600"
                          style={{
                            backgroundColor: c
                              ? cellColor(c.probability)
                              : "#e5e5e5",
                            color:
                              c && c.probability >= 0.8 ? "white" : undefined,
                            outline:
                              i + 1 === period
                                ? "2px solid #ea580c"
                                : undefined,
                          }}
                        >
                          {c ? Math.round(c.probability * 100) : "—"}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-neutral-500">
          Valores em %. Intervalos de Wilson de 95% descrevem a frequência
          histórica; a incerteza da conversão entre sensores e as mudanças
          climáticas não estão totalmente representadas.
        </p>
      </div>
    </section>
  );
}
