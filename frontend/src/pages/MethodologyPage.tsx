export function MethodologyPage() {
  return (
    <section className="max-w-3xl space-y-6 text-sm leading-6">
      <h1 className="text-2xl font-semibold">Como interpretar os dados</h1>
      <article className="rounded-xl border p-5 dark:border-neutral-800">
        <h2 className="font-semibold">Uma referência: VIIRS</h2>
        <p>
          Os registros originais NASA FIRMS são preservados. A análise usa
          subcélulas ocupadas de 0,01° por dia UTC e por passagem
          diurna/noturna, reunidas em áreas de 0,5°. Não é uma contagem de
          incêndios nem de pixels VIIRS de 375 m.
        </p>
        <p>
          Para cada dia, selecionamos uma única fonte VIIRS com cobertura
          confirmada: S-NPP, depois NOAA-20 e NOAA-21; SP tem prioridade sobre
          NRT do mesmo satélite. Isso evita somar passagens de vários satélites.
          Transições entre plataformas ainda podem introduzir diferenças.
        </p>
        <p>
          Aqua MODIS é calibrado em meses completos compartilhados com VIIRS na
          mesma área. O fator é a mediana das razões mensais; a incerteza vem de
          reamostragem de anos. A validação retira um ano inteiro de cada vez e
          compara o erro com a conversão neutra. Exigimos 6 meses e 3 anos de
          sobreposição. MODIS sem calibração aprovada é excluído da série
          equivalente. Terra fica de fora por seu horário de passagem diferente.
        </p>
        <p>
          Um dia coberto com zero VIIRS permanece zero; não é substituído por
          MODIS. Conversão estatística não recupera a resolução espacial do
          sensor VIIRS.
        </p>
      </article>
      <article className="rounded-xl border p-5 dark:border-neutral-800">
        <h2 className="font-semibold">Calendário semanal e mensal</h2>
        <p>
          A probabilidade é a fração dos anos cobertos em que a área apresentou
          ao menos uma unidade de atividade equivalente. Dias sem detecção
          entram como zero apenas quando a aquisição e ingestão da área nacional
          foram verificadas. Períodos incompletos e o período em andamento são
          excluídos. São necessários 3 anos completos para publicar uma
          estimativa.
        </p>
        <p>
          Semanas seguem o calendário ISO (segunda a domingo, inclusive a semana
          53 quando existir). O intervalo de Wilson de 95% representa a
          incerteza amostral da frequência; não inclui toda a incerteza entre
          sensores. O Brier é calculado apenas com anos anteriores a cada ano de
          teste. Sem anos de teste suficientes, a validação aparece como
          indisponível.
        </p>
        <p>
          O ano de planejamento posiciona as semanas e meses em datas futuras. A
          probabilidade continua sendo histórica: não incorpora previsão
          meteorológica, ignições humanas ou mudanças recentes no uso do solo.
          Não há garantia de ocorrência.
        </p>
      </article>
      <article className="rounded-xl border p-5 dark:border-neutral-800">
        <h2 className="font-semibold">Mapas e localização</h2>
        <p>
          Plano usa projeção Mercator, Globo usa projeção esférica, e Relevo 3D
          combina elevação real com câmera inclinada. A camada de calor mostra
          concentração suavizada de atividade; ela não representa temperatura.
        </p>
        <p>
          O território nacional é recortado pelas malhas oficiais simplificadas
          do IBGE. Os filtros estaduais usam o ponto representativo da área de
          0,5°; células na divisa podem conter atividade de mais de um estado.
          Coordenadas indicam a área analisada, não a localização exata de
          futuros focos. Detecção de satélite não confirma incêndio; nuvens e
          condições de observação podem ocultar atividade.
        </p>
      </article>
      <p className="text-xs text-neutral-500">
        Fontes: NASA FIRMS (MODIS/VIIRS), IBGE (limites), OpenStreetMap/NASA
        GIBS (base), Mapzen/AWS (elevação).
      </p>
    </section>
  );
}
