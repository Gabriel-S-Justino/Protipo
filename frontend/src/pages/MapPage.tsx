import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { useScope } from "@/app/Scope";
import { FireMapView, type MapMode } from "./FireMapView";
const MODES: { id: MapMode; label: string }[] = [
  { id: "flat", label: "Plano" },
  { id: "globe", label: "Globo" },
  { id: "terrain", label: "Relevo 3D" },
];
function iso(d: Date) {
  return d.toISOString().slice(0, 10);
}
export function MapPage({ initialMode }: { initialMode: MapMode }) {
  const { regionId, name, bbox } = useScope();
  const [mode, setMode] = useState(initialMode);
  useEffect(() => setMode(initialMode), [initialMode]);
  const [from, setFrom] = useState(() =>
    iso(new Date(Date.now() - 30 * 86400000)),
  );
  const [to, setTo] = useState(() => iso(new Date()));
  const valid = from < to;
  const q = useQuery({
    queryKey: ["heat", regionId, from, to],
    queryFn: () => api.heat(regionId, from, to),
    enabled: valid,
  });
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Calor no território · {name}</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Histórico unificado na escala VIIRS. Explore a concentração espacial e
          escolha o período.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex rounded-lg border border-neutral-300 p-1 dark:border-neutral-700">
          {MODES.map((m) => (
            <button
              key={m.id}
              aria-pressed={mode === m.id}
              onClick={() => setMode(m.id)}
              className={`rounded px-3 py-2 text-sm ${mode === m.id ? "bg-orange-600 text-white" : ""}`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <label className="text-xs">
          De
          <input
            aria-label="Data inicial"
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="ml-2 rounded border bg-transparent p-2"
          />
        </label>
        <label className="text-xs">
          Até (exclusivo)
          <input
            aria-label="Data final"
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="ml-2 rounded border bg-transparent p-2"
          />
        </label>
      </div>
      {!valid && (
        <p role="alert">Escolha uma data final posterior à inicial.</p>
      )}
      {q.isFetching && (
        <p role="status" className="text-sm text-neutral-500">
          Atualizando atividade…
        </p>
      )}
      {q.error && (
        <p
          role="alert"
          className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"
        >
          {q.error.message}
        </p>
      )}
      {q.data && !q.data.features.length && (
        <p className="rounded border p-3 text-sm">
          Sem atividade processada neste intervalo. Consulte Dados e qualidade
          para verificar a cobertura; isso não confirma ausência de fogo.
        </p>
      )}
      <FireMapView
        mode={mode}
        regionBbox={bbox}
        data={valid ? q.data : undefined}
      />
    </section>
  );
}
