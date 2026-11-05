# VERCEL (limites, validações e passo a passo)

> Este arquivo registra as **validações reais** exigidas pelo PromptMaster §1.3
> e o byte a byte do deploy. Atualize a cada mudança da plataforma.

## Validações feitas (2026-11-05)

- FIRMS Area API **sem chave**: resposta `"Invalid MAP_KEY."` com HTTP 400 — endpoint confirmado
  (`/api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}/{DATE}`).
- **MAP_KEY**: obter em `https://firms.modaps.eosdis.nasa.gov/api/map_key/` (conta Earthdata).
- GIBS WMTS: `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml` (sem chave),
  camadas confirmadas: `BlueMarble_NextGeneration`, `BlueMarble_ShadedRelief`,
  `VIIRS_SNPP_CorrectedReflectance_TrueColor`, `VIIRS_NOAA20_CorrectedReflectance_TrueColor`.
- Neon/Supabase: **limites do plano a confirmar no primeiro deploy** (armazenamento, computação, conexões, suporte a PostGIS).

## Limites a confirmar no primeiro deploy (checklist)

- [ ] Runtime Python: empacotamento atual de FastAPI/ASGI (entrypoint `api/index.py`).
- [ ] Instalação de `pip install -r api/requirements.txt` (build).
- [ ] Duração máx. e memória configuradas em `vercel.json#functions` (usamos 30s/1024MB como ponto de partida).
- [ ] Peso do bundle da função (< limite do plano; manter sem deps científicas).
- [ ] Vercel Cron (se ativado) e `CRON_SECRET`.

## config do projeto (vercel.json)

- **Frontend**: build do Vite → `frontend/dist` estático; rewrites `/api/(.*)` → `/api/index.py` e fallback do SPA (arquivos estáticos têm precedência sobre rewrites).
- **Headers de cache**: tiles MVT (1h/CDN 24h), assets com hash (imutável).
- **Segurança**: CORS via `CORS_ORIGINS` restrito; sem `*` em produção. Rate limit básico a adicionar (middleware SlowAPI) na fase 7.

## Variáveis de ambiente por ambiente

| Variável | Dev | Preview | Production | Fonte |
|----------|-----|---------|------------|-------|
| `DATABASE_URL`            | Neon branch dev | Neon branch preview | Neon prod | Marketplace/Neon |
| `DATABASE_URL_DIRECT`     | idem | idem | idem | Neon direct |
| `MAP_KEY`                 | local .env | secrets repo (CI) | pipeline only | Earthdata |
| `ADMIN_TOKEN`             | dev | — | Vercel secret | |
| `CRON_SECRET`             | dev | — | Vercel secret | |
| `CORS_ORIGINS`            | http://localhost:5173 | preview domain | domínio prod | |
| `VITE_API_BASE_URL`       | vazio (usa /api) | preview domain | domínio prod | |
| `VITE_CESIUM_ION_TOKEN`   | público (restrito por domínio) | idem | idem | Cesium ion |

## Passo a passo de deploy (resumo)

1. `vercel login` e `vercel link` no diretório do monorepo.
2. Criar o banco (Neon no Marketplace) e **habilitar PostGIS** (`CREATE EXTENSION postgis`).
3. Definir as env keys da tabela acima (Preview/Production no painel; `.env` local).
4. Rodar migrations a partir do local (nunca da function):
   `cd backend && DATABASE_URL_DIRECT=... alembic upgrade head`
5. Primeiro deploy (sem dados): `vercel deploy` → `GET /api/health deve responder "degraded" (DB vazio é ok)`.
6. Pipeline: `python -m pipeline seed-demo --rows 5000` para DEMO, ou ingestão real quando MAP_KEY estiver.
7. Conectar repositório para preview deployments por branch/PR.

## Projeto único (monorepo) × dois projetos

Decisão: **um projeto**. O frontend e a API compartilham rewrites e headers,
o pipeline nunca entra no deploy (`.vercelignore` excluir `pipeline/`, `data/`, `docs/`).
