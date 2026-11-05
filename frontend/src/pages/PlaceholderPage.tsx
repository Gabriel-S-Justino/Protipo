/** Página de marcador HONESTO para módulos de fases futuras. Sem dados falsos. */
export function PlaceholderPage({ title, phase }: { title: string; phase: string }) {
  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">{title}</h1>
      <div className="max-w-prose rounded-lg border border-neutral-200 bg-white p-6 text-sm dark:border-neutral-800 dark:bg-neutral-900">
        <p className="font-medium">Em construção — {phase}.</p>
        <p className="mt-2 text-neutral-600 dark:text-neutral-400">
          Este módulo não foi implementado ainda nesta fase incremental. Não exibimos placeholders
          de dados: quando ativado, esta tela apresentará somente dados reais (NASA FIRMS/GIBS, IBGE)
          pré-calculadas pelo pipeline.
        </p>
      </div>
    </section>
  );
}
