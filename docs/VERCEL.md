# VERCEL (limites, validações e passo a passo)

> Este arquivo registra as **validações reais** exigidas pelo PromptMaster §1.3
> e o byte a byte do deploy. Atualize a cada mudança da plataforma.

## Validações feitas (changelog de deploy)

- **Deploy real #1** (2026-11-05, projeto "Protipo", iad1): build do frontend ✔; instalação da
  function falhou com `externally-managed-environment` (Python do builder é gerenciado pelo
  `uv`, PEP 668). **Correção**: `pip install --break-system-packages` no `installCommand`
  (`vercel.json`). Documentação do comportamento do builder (Python uv-managed) registrada aqui.

## Painel de diagnósticos reais validados durante o deploy

- **Pooler do Neon**: REJEITA startup parameter `options: statement_timeout`
  (`unsupported startup parameter in options`); só funciona com unpooled ou removendo-o.
  Implementado: sem `options` no `connect_args` (`backend/app/core/db.py`); timeout de sessão
  opcional via `SET statement_timeout=...` no SQL quando necessário.
- Região do Neon criada: `us-east-1` (iad1) — endpoint `ep-rough-frost-...`.

## Validações de APIs (2026-11-05)

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
| `DATABASE_URL`            | Neon branch dev | injetada pela integração | injetada pela integração | integração Vercel×Neon (autom.) |
| `DATABASE_URL_DIRECT`     | .env local | opcional | opcional (usa `DATABASE_URL_UNPOOLED`) | manual |
| `DATABASE_URL_UNPOOLED`   | — | injetada | injetada | integração Vercel×Neon (autom.) |
| `ADMIN_ENABLED` / `ADMIN_TOKEN` | dev | true+token | true+token (p/ migrations 1x) | manual (valor forte) |
| `MAP_KEY`                 | .env local | secrets repo (CI) | pipeline only | Earthdata |
| `CRON_SECRET`             | dev | — | Vercel secret | |
| `CORS_ORIGINS`            | http://localhost:5173 | preview domain | domínio prod | |
| `VITE_API_BASE_URL`       | vazio (usa /api) | preview domain | domínio prod | |
| `VITE_CESIUM_ION_TOKEN`   | público (restrito por domínio) | idem | idem | Cesium ion |

## Passo a passo de deploy — FLUXO SEM MUDANÇAS DE CÓDIGO

O projeto está preparado para: **push no GitHub → deploy na Vercel → criar banco pela
aba Database (integração Neon) → aplicar migrations via API admin**. Sem editar nada no código.

1. **Deploy do repositório**
   - Vercel Dashboard → **Add New → Project → Import** repositório GitHub.
   - Framework: detecta Vite (root override não necessário; `vercel.json` guia o build).
   - Primeiro deploy: frontend ✔ e API `/api/health` responde
     `"database": "aguardando integração Vercel×Neon"` (degradado, esperado e saudável).

2. **Criar o banco pela integração (sem editar código)**
   - Dashboard → **Storage → Create Database → Neon (Marketplace)** (plano Free).
   - Região sugerida: **Frankfurt (fra1)** (menor latência Brasil↔Vercel).
   - Depois de criar, marque **Connect to project** (ou a própria criação já conecta).
   - A integração injeta AUTOMATICAMENTE no deploy:
     - `DATABASE_URL` (pooled) e `DATABASE_URL_UNPOOLED` (direta).
   - O código resolve essas variáveis automaticamente
     (`backend/app/core/config.py`, `pipeline/config.py`, `backend/migrations/env.py`).
     `DATABASE_URL_DIRECT` manual é OPCIONAL (continua suportada com precedência).

3. **Circular as migrations UMA VEZ (via API admin, direto da Vercel)**
   - Env vars no projeto (Production): `ADMIN_ENABLED=true`, `ADMIN_TOKEN=<valor forte>`.
   - Redeploy (para aplicar as novas env) → depois:
     ```bash
     curl -X POST https://SEU-DEPLOY.vercel.app/api/admin/migrate \
       -H "X-Admin-Token: SEU_TOKEN"
     ```
   - Resposta: `{"status":"ok","revision_before":null,"revision_after":"0001_initial"}`.
   - Alternativa local (igualmente válida): `npm run db:migrate` com as URLs no `.env`.
   - Depois pode manter ADMIN_ENABLED=true (uso para re-migrar) ou voltar `false`.

4. **Dados**
   - DEMO: `python -m pipeline seed-demo` (local; `is_demo=true` e UI rotula).
   - Real: `python -m pipeline ingest <csv>` local ou via GitHub Actions agendado
     (secrets `MAP_KEY`, `DATABASE_URL_DIRECT` — ver `.github/workflows/pipeline.yml`).

5. **Validação do primeiro deploy (checklist técnico)**
   - [ ] `GET /api/health` → `status:"ok"` e `database:"up (N tabelas)"`.
   - [ ] `GET /api/dashboard/summary` → números zero mas `200` (banco conectado).
   - [ ] Function Python empacotou (verificar em `Deploy → Functions` sem erro de build).
   - [ ] Bundle inclui backend (config `includeFiles: "backend/**"` nos `functions`).

## Projeto único (monorepo) × dois projetos

Decisão: **um projeto**. O frontend e a API compartilham rewrites e headers,
o pipeline nunca entra no deploy (`.vercelignore` excluir `pipeline/`, `data/`, `docs/`).
