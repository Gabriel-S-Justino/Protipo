/** Barra superior: região, período e indicador da série de referência. */
export function TopBar() {
  return (
    <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-3 dark:border-neutral-800">
      <div className="flex items-center gap-3 text-sm">
        <span data-testid="region-filter" className="rounded bg-neutral-100 px-2 py-1 dark:bg-neutral-800">
          Região: Ceará
        </span>
        <span className="rounded bg-neutral-100 px-2 py-1 dark:bg-neutral-800">
          Período: 2000 → atual
        </span>
      </div>
      <span className="text-xs text-neutral-500">
        Referência: <strong>VIIRS</strong> (série unificada · MODIS harmonizado 2000–2011)
      </span>
    </header>
  );
}
