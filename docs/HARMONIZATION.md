# HARMONIZATION (MODIS → escala VIIRS) — design da fase 4

Resultado: **uma série única na escala VIIRS**, com incerteza e proveniência.
Originais intactos em `fire_detections`; a unificação acontece em tabelas derivadas
(`harmonized_series`, `harmonization_models`) e o pipeline calcula offline.

## Princípios (inegociáveis)

- Onde há VIIRS, usa-se **VIIRS direto**. A transformação só se aplica a períodos
  com apenas MODIS (≈2000–2011).
- Corresponder pixels é **diagnóstico**, não o método: agregamos na MESMA grade e
  janela temporal (célula × dia/semana/mês, separando dia/noite).
- Controle de qualidade: relação instável ou amostra insuficiente →
  `quality_flag = 'low_confidence' | 'insufficient'` (nunca forjar um número).

## Diferenças físicas tratadas

| Aspecto | MODIS (Terra/Aqua) | VIIRS 375 m | Tratamento |
|---------|--------------------|-------------|------------|
| Resolução | ~1 km | 375 m; detecta menor/frio | modelagem nível-célula (contagem) |
| Horário | Aqua ~13h30/01h30 (análogo) | ~13h30/01h30 | calibrar Aqua×S-NPP; Terra excluída por padrão |
| Terra ~10h30 | sem análogo VIIRS | — | `use_terra=false`; opcional com ajuste diurno documentado |
| Varredura | pixel cresce fora do nadir | — | evitar margens extremas na calibração |
| Confiança | 0–100 | l/n/h | normalização ordinal documentada (l=0, n=50, h=100) |
| FRP | ~1:1 não equivalente | — | FRP harmonizado marcado como estimado |

## Estratégia de conversão (§ 6.3 do master)

1. **Calibrar na sobreposição** Aqua MODIS × VIIRS S-NPP (2012 → desativação do Aqua).
2. **Agregar** ambos na grade/célula comuns; colunas em dia/noite.
3. **Modelar** contagem_VIIRS = f(contagem_MODIS, região, estação, dia/noite):
   - linha de base: razão e regressão robusta por região e estação;
   - modelos de contagem (Poisson/Binomial Negativa) com termos sazonais/regionais,
     apenas se a validação justificar; opcional quantile mapping.
4. **Validação obrigatória**: leave-one-year-out na sobreposição; métricas:
   erro absoluto, viés, correlação, cobertura do IC e estabilidade ao longo dos anos.
5. **Incerteza**: bootstrap por ano/bloco → propagada até série e calendário.
6. **Relatório**: gráficos de calibração, decisão final e versionamento (`harmonization_models`).

## Continuidade entre satélites VIIRS

- Verificar consistência S-NPP × NOAA-20 × NOAA-21; ajuste documentado se necessário.
- Nunca somar detecções de vários satélites VIIRS sem deduplicação — a unidade
  de análise é "dia-célula com detecção" e "contagem deduplicada".
