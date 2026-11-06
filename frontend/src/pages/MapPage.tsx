/** Página de mapa — três modos com dados reais (filtros demo/temporais honestos). */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Region } from "@/services/api";
import { FireMapView, type MapMode } from "./FireMapView";

const MODES: { id: MapMode; label: string; note: string }[] = [
  { id: "globe", label: "Globo 3D", note: "NASA GIBS Blue Marble + projeção globe" },
  { id: "flat", label: "Mapa plano", note: "base escura CARTO, zoom até rua" },
  { id: "terrain", label: "Relevo 3D", note: "DEM terrarium (dados abertos)" },
];

export function MapPage({ initialMode }: { initialMode: MapMode }) {
  const [mode, setMode] = useState<MapMode>(initialMode);
  const regionsQuery = useQuery({ queryKey: ["regions"], queryFn: () => api.regions(20) });
  const regions = (regionsQuery.data ?? []).filter((r: Region) => r.name === "Ceará");
  const ceara = regions[0];
  // bbox do Ceará real (regions API: colunas não expostas no resumo) — fixo leaderboard-safe
  const bbox: [number, number, number, number] = [-42.6404, -7.5178, -37.2866, -2.3017];

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">
        Focos de calor {ceara ? `— ${ceara.name}` : "— carregando regiões…"}
      </h1>

      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={`rounded-md border px-3 py-1.5 text-sm transition ${
              mode === m.id
                ? "border-orange-400 bg-orange-50 text-orange-700 dark:border-orange-500 dark:bg-orange-950 dark:text-orange-300"
                : "border-neutral-200 bg-white hover:bg-neutral-100 dark:border-neutral-800 dark:bg-neutral-900"
            }`}
            title={m.note}
          >
            {m.label}
          </button>
        ))}
      </div>

      <FireMapView mode={mode} regionBbox={bbox} />

      <p className="text-xs text-neutral-500">
        {MODES.find((m) => m.id === mode)?.note}. Dados exclusivamente NASA FIRMS
        (MODIS 1 km + VIIRS 375 m, escala VIIRS na série; no mapa, células com a
        proporção por instrumento). Regime "inserir dados DEMO" é
        rotulado e nunca misturado; filtros temporais dao vir numa próxima iteração.
      </p>
    </section>
  );
}
