# CALENDAR_MODEL (fase 5 — implementado)

> Implementado em `pipeline/analytics.py` (`python -m pipeline calendar --region 1`):
> P(≥1 foco) por mês civil = fração de anos com ≥1 foco na região (dados reais,
> is_demo=FALSE), `years_used` e `confidence` honestos; API lê
> `/api/calendar/probability?period_type=month`.
> Anomalias: `python -m pipeline anomalies --region 1` (z-score por mês civil;
> baseline < 3 anos ⇒ level 'info' com nota) → `/api/analytics/anomalies`.


Objetivo: calendário probabilístico por região/ano — estatística histórica calibrada,
NUNCA previsão determinística de incêndios. Gravado em `calendar_probabilities` pelo
pipeline (`python -m pipeline calendar`).

## Alvo (§ 8.1)

- Unidade única por célula do calendário: `P(≥ 1 foco VIIRS-equivalente na região durante a semana s)`.
- Opcional: contagem esperada (`expected_count`) e FRP esperado.
- Unidade espacial-temporal: escolhe-se conforme o volume real (semana × município como padrão;
  célula da grade para regiões grandes). Definição final após medir o volume (§ 3.3).

## Métodos (do simples ao complexo; avança apenas se a validação justificar)

1. **Climatologia empírica** por semana do ano com suavização circular (fim(início) do ano conectados).
2. **Modelo sazonal**: regressão logística/Poisson com harmônicos de Fourier,
   efeito de região e tendência; intervalos via Beta-binomial bayesiano ou bootstrap.
3. Opcional: covariáveis (precipitação POWER/IMERG, ENSO, NDVI) apenas se
   melhorarem a métrica fora da amostra.

## Backtesting (§ 8.3)

- Por ano: treina até N-1, avalia N — Brier score, log-loss, calibração, AUC.
- Comparar sempre com a linha de base ingênua (climatologia simples); reportar se
  o modelo complexo realmente ganha.
- Amostra insuficiente → célula marcada **"dados insuficientes"** (interface mostra isso).

## Apresentação (§ 8.4)

- Mapa de calor semana × região; visão mensal/diária; comparação ano corrente
  (observado vs esperado); como exportar CSV/PNG; fica implementado na fase 6/7 da UI.
- Interface usa SEMPRE "probabilidade histórica".
