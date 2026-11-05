/** Metodologia (§11.2.10): fontes, harmonização, modelo do calendário, limitações, citações. */
export function MethodologyPage() {
  return (
    <section className="prose prose-sm max-w-3xl space-y-6 text-sm leading-6">
      <h1 className="text-xl font-semibold">Metodologia</h1>

      <div className="rounded-lg bg-white p-5 shadow-sm dark:bg-neutral-900">
        <h2 className="mb-2 font-semibold">Fontes de dados</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>NASA FIRMS</strong>: MODIS C6.1 (Terra/Aqua, ~1 km) e VIIRS 375 m
            (S-NPP desde 2012; NOAA-20 desde 2018; NOAA-21 desde 2024). Fontes SP (reprocessadas)
            priorizadas para o histórico; NRT completa o período recente (regra de substituição documentada).
          </li>
          <li><strong>NASA GIBS</strong>: contexto visual (Blue Marble, Corrected Reflectance) — não alimenta a análise.</li>
          <li><strong>IBGE</strong>: malhas municipais/estaduais dos limites administrativos.</li>
        </ul>
      </div>

      <div className="rounded-lg bg-white p-5 shadow-sm dark:bg-neutral-900">
        <h2 className="mb-2 font-semibold">Harmonização MODIS → escala VIIRS</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>VIIRS é o sensor de referência; a série unificada toma a resolução/janela do VIIRS.</li>
          <li>Calibração no período de sobreposição Aqua MODIS × VIIRS (2012→desativação do Aqua), mesmo horário de passagem.</li>
          <li>Conversão modelada por região/estação/dia-noite (razão e regressão robusta como linha de base; modelos de contagem quando justificado).</li>
          <li>Incerteza via bootstrap por ano/bloco, propagada até a série e ao calendário.</li>
          <li>Relação instável ou amostra insuficiente → rotulada "harmonização de baixa confiança" ou "insuficiente". Nunca se força um número.</li>
        </ul>
      </div>

      <div className="rounded-lg bg-white p-5 shadow-sm dark:bg-neutral-900">
        <h2 className="mb-2 font-semibold">Calendário de probabilidade</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Alvo: P(≥ 1 foco VIIRS-equivalente na região durante a semana s).</li>
          <li>Métodos: climatologia empírica com suavização circular → modelo sazonal logístico/Poisson com harmônicos apenas se o backtesting justificar.</li>
          <li>Validação: backtesting por ano (treina até N-1, avalia N): Brier score, log-loss, calibração, AUC.</li>
          <li>Cada célula mostra probabilidade, IC 95%, nº de anos usados, parcela harmonizada vs. direta e nível de confiança.</li>
        </ul>
      </div>

      <div className="rounded-lg bg-white p-5 shadow-sm dark:bg-neutral-900">
        <h2 className="mb-2 font-semibold">Limitações fundamentais</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Detecção de satélite <strong>não</strong> é incêndio confirmado; ausência de detecção não é ausência de fogo.</li>
          <li>Terra (passagem matinal) não tem análogo VIIRS; por padrão fica fora da série principal.</li>
          <li>S-NPP interrompe atualização operacional da FIRMS em 2/11/2026 (histórico persiste).</li>
          <li>Probabilidade do calendário é <strong>estatística histórica calibrada</strong>, não previsão determinística.</li>
        </ul>
      </div>

      <p className="text-xs text-neutral-500">
        Créditos: MODIS (NASA/Terra-Aqua), VIIRS (NASA/NOAA Suomi-NPP, NOAA-20, NOAA-21),
        FIRMS/GIBS (NASA EOSDIS), malhas IBGE.
      </p>
    </section>
  );
}
