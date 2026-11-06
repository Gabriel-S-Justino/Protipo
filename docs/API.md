# API (§ 12 do master prompt)

Base **/api** (na Vercel: rewrites para `api/index.py`; local: `uvicorn backend.app.main:app`).
Documentação interativa: `/api/docs` (Swagger UI) e `/api/redoc`; OpenAPI JSON: `/api/openapi.json`.

Todas as respostas com erros padronizados `{"error": ..., "detail": ...}`, limites máximos
(pagination ≤ `max_limit`) e cache HTTP quando seguro.

| Endpoint (GET)              | Status atual | Descrição |
|-----------------------------|--------------|-----------|
| `/api/health`               | ✔ implementado | status, env, banco (up/degraded) |
| `/api/dashboard/summary`    | ✔ implementado      | totais, 30d, média histórica (lê o banco) |
| `/api/metadata/coverage`    | ✔ implementado      | cobertura temporal/instrumentos/parcela harmonizada |
| `/api/calendar/probability` | ✔ implementado      | células pré-calculadas por semana/mês |
| `/api/series/unified`       | ✔ implementado      | série unificada com incerteza/proveniência |
| `/api/series/seasonality`   | ✔ implementado      | climatologia por semana (usar com cuidado) |
| `/api/detections`, `/{id}`  | ✔ implementado      | listagem paginada de originais |
| `/api/regions`, `/{id}/summary` | ✔ implementado  | regiões analíticas (bbox p/ Ceará até malha IBGE) + ficha (totals, mensal 36 m, top células 0,25°) |
| `/api/analytics/anomalies`  | ✔ implementado      | ler `anomaly_results` (z-score mensal; nível + nota de honestidade) |
| `/api/ingestion/batches`    | ✔ implementado      | lotes de ingestão (fonte, aceitos/rejeitados/duplicados) |
| `/api/metadata/sources`     | ✔ implementado      | fontes com detecções/primeira-última sobrevoo |
| `/api/tiles/{layer}/{z}/{x}/{y}.mvt` | ✔ implementado | `grid_points` MVT via PostGIS `ST_AsMVT` (grade tile/8; `include_demo`, `from`, `to`) |
| `/api/harmonization/*`      | fase 4              | modelos/relatório de calibração (dados em `harmonization_models`) |
| `/api/admin/migrate` (POST) | fase: implementado no fluxo de deploy | aplica migrations Alembic (X-Admin-Token; ADMIN_ENABLED=true) |
| `/api/admin/*` demais       | fase 7              | protegido por ADMIN_TOKEN; OFF por padrão |

## Segurança

- CORS restrito (`CORS_ORIGINS`; `*` proibido em produção); métodos GET apenas.
- Todas as consultas parametrizadas (anti-SQL injection, mesmo em tiles).
- `statement_timeout` por conexão (`QUERY_TIMEOUT_MS`; default 5s).
- Usuário do banco da API: privilégio mínimo (leitura); usuário separado para o pipeline.
