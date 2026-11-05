# Fire Intelligence Platform

Plataforma de inteligência ambiental que unifica os históricos **MODIS** e **VIIRS** em uma única série
(escala VIIRS) e gera um **calendário probabilístico de focos de calor** por região.

- Região inicial: **Ceará, Brasil** (extensível a qualquer estado/país).
- **Sem Docker**. Deploy pronto para a **Vercel** (SPA + API serverless + Postgres/PostGIS gerenciado).
- Pipeline científico roda **fora da Vercel** (local e GitHub Actions agendado).

```
NASA FIRMS / GIBS
        │ download
        ▼
Pipeline Python (local / GitHub Actions)
        │ grava (conexão direta)
        ▼
PostgreSQL + PostGIS (Neon via Vercel Marketplace, ou Supabase)
        ▲ lê (conexão pooled)
        │
API FastAPI  →  Vercel Functions (Python)
        ▲ /api/*
SPA React (Vite) → Vercel estático
```

## Estrutura

```
frontend/            SPA React + TypeScript + Vite (tailwind)
api/                 entrypoint das Vercel Functions (FastAPI)
backend/             código da API (app/, migrations/, tests/, requirements.txt)
pipeline/            pipeline científico — NÃO vai para a Vercel
database/seeds/      seeds (DEMO)
data/                raw/processed/boundaries/reports — fora do Git
docs/                documentação (PT-BR)
.github/workflows/   CI e pipeline agendado
scripts/             utilitários multiplataforma
```

Referência rápida de operação (para o passo a passo completo, ver `docs/VERCEL.md`).

## Deploy “está pronto”: fluxo sem mudanças de código

1. `git push` → Vercel importa o repo e faz o deploy (frontend ✔ + API ✔ `/api/health`).
2. Painel Vercel → **Storage → Create Database → Neon** → conecta ao projeto →
   a integração injeta `DATABASE_URL`/`DATABASE_URL_UNPOOLED` automaticamente (o código já lê).
3. Definir `ADMIN_ENABLED=true` e `ADMIN_TOKEN` (env Production) → redeploy →
   `curl -X POST .../api/admin/migrate -H "X-Admin-Token: ..."` → PostGIS + 11 tabelas criadas.
4. (Opcional) `npm run db:migrate` local faz o mesmo, com URLs no `.env`.
5. Pipeline (`python -m pipeline`) para DEMO/ingestão real.

## Início rápido

Veja `docs/SETUP.md` para detalhes (Windows/macOS/Linux).

```bash
# Frontend
npm install --prefix frontend
npm run dev --prefix frontend

# API local
python -m venv .venv && . source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload                 # http://localhost:8000/api/docs

# Pipeline
pip install -r pipeline/requirements.txt
python -m pipeline --help
python -m pipeline seed-demo --rows 5000              # dados sintéticos DEMO (is_demo = true)
```

Cópia de `.env.example` → `.env` é obrigatória para o pipeline e para a API (variáveis listadas no arquivo).

## Status da implementação

Progresso guiado em fases (ver `docs/ARCHITECTURE.md`): base do projeto/migrations →
ingestão FIRMS idempotente → harmonização MODIS→VIIRS → calendário/anomalias →
interface completa (3 mapas, calendário, séries) → qualidade/produção.

## Fontes e créditos

Dados: **NASA FIRMS** (MODIS C6.1, VIIRS 375 m S-NPP/NOAA-20/NOAA-21) e **NASA GIBS** para contexto visual.
Limites administrativos: **IBGE**. Detecção de satélite **não** é incêndio confirmado;
o calendário apresenta **estatística histórica calibrada**, nunca previsão determinística.
