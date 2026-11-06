# Fire Intelligence · Brasil

Mapas Plano, Globo e Relevo 3D com atividade de calor harmonizada na escala VIIRS.
Calendário por localização, semana ISO e mês, com frequência histórica, intervalo de
95%, anos cobertos e validação temporal.

## Arquitetura
React/TypeScript/Vite → API FastAPI → PostgreSQL 15+ com PostGIS.
O pipeline Python coleta, harmoniza e calcula os produtos fora da Vercel.
Malhas oficiais do IBGE delimitam Brasil e as 27 UFs. Não há restrição ao Ceará.

## Preparar os dados
1. Instale as dependências de `backend/requirements.txt`, `pipeline/requirements.txt` e `frontend/package.json`.
2. Configure `.env` a partir de `.env.example`: `DATABASE_URL`, `DATABASE_URL_DIRECT`, `MAP_KEY`.
3. Aplique `alembic -c backend/alembic.ini upgrade head`.
4. Execute `python -m pipeline boundaries` (importa os limites oficiais).
5. Consulte `python -m pipeline status --sensor VIIRS_SNPP_SP` e as demais fontes.
6. Faça backfill de janelas disponíveis de MODIS_SP, VIIRS_SNPP_SP e, para continuidade,
   VIIRS_NOAA20_SP/NRT e VIIRS_NOAA21_SP/NRT.
7. Execute `python -m pipeline harmonize`, `python -m pipeline calendar`,
   `python -m pipeline anomalies`.

Exemplo de backfill **restrito a 3 janelas de teste**:
```sh
python -m pipeline backfill --source VIIRS_SNPP_SP --start 2020-01-01 --end 2020-01-15 --limit 3
```
Isso não produz um calendário confiável. São necessários pelo menos 3 anos com
períodos completos por localização; use intervalos históricos reais disponíveis.

`fetch` grava CSV e metadados JSON de cobertura. Para ingestão manual:
`python -m pipeline ingest data/raw/ARQUIVO.csv --source FONTE`.
Mantenha o JSON ao lado do CSV. Um CSV isolado não comprova cobertura de dias sem focos.
Caches antigos do Ceará não contam como aquisição nacional.

## Rodar e verificar
```sh
npm --prefix frontend install
npm --prefix frontend run dev
uvicorn backend.app.main:app --port 8000
python -m pytest -q backend/tests pipeline/tests
npm --prefix frontend run build
```
`scripts/test_browser.cjs` verifica o preview na porta 4173 com fixtures isoladas
do navegador, sem inserir dados fictícios no produto.
O workflow diário executa `python -m pipeline update`; requer limites já importados
e secrets `MAP_KEY` e `DATABASE_URL_DIRECT`.

## Interpretação
Uma única fonte VIIRS por dia; MODIS Aqua convertido somente com calibração por
área aprovada em validação por ano. Não somamos os sensores.
Unidade: subcélulas ocupadas de 0,01° por dia UTC e passagem diurna/noturna.
Áreas de análise de 0,5° (~50 km); a conversão não recupera a resolução de 375 m.
O calendário é recorrência histórica para planejamento, não previsão meteorológica
nem garantia de incêndio. Veja [a metodologia](docs/HARMONIZATION.md) e
[o calendário](docs/CALENDAR_MODEL.md).

Mudanças locais precisam ser publicadas e a carga nacional precisa ser executada
no ambiente com banco e chave FIRMS para aparecerem em produção.
