import { useScope } from "@/app/Scope";
export function TopBar() {
  const { regionId, setRegionId, regions } = useScope();
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200 bg-white px-6 py-3 dark:border-neutral-800 dark:bg-neutral-900">
      <label className="flex items-center gap-3 text-sm">
        Área de análise
        <select
          aria-label="Área de análise"
          className="rounded border border-neutral-300 bg-transparent px-3 py-2 dark:border-neutral-700"
          value={regionId ?? ""}
          onChange={(e) =>
            setRegionId(e.target.value ? Number(e.target.value) : undefined)
          }
        >
          <option value="">Brasil inteiro</option>
          {regions
            .filter((r) => r.level === "state")
            .map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
        </select>
      </label>
      <span className="text-xs text-neutral-500">
        Uma série · escala VIIRS · histórico e probabilidade por área
      </span>
    </header>
  );
}
