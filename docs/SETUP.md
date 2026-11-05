# SETUP (Windows · macOS · Linux)

## 1. Pré-requisitos

- **Node LTS** (validado com Node 24) e npm ≥ 10.
- **Python 3.x** (validado com Python 3.14; requer wheels cp314 — ver abaixo).
- **Vercel CLI**: `npm i -g vercel` (Windows/macOS/Linux iguais).
- **Postgres+PostGIS gerenciado**: recomendado criar um projeto **Neon** (via Vercel Marketplace)
  ou Supabase. Alternativa local: systemd/postgres instalado com extensão PostGIS (sem Docker).
- Dica multiplataforma: os comandos abaixo funcionam igualmente em PowerShell/cmd/bash
  (com pequenas variações de operador: `set`/`$env:` em Windows para variáveis).

## 2. Clonar e instalar

```bash
git clone <repo> && cd <repo>
npm install --prefix frontend            # instala deps do SPA
python -m venv .venv
. .venv/bin/activate                     # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r pipeline/requirements.txt
```

## 3. Environment

Copie `.env.example` para `.env`, edite:

- `DATABASE_URL` (pooled; para a API/Vercel) e `DATABASE_URL_DIRECT` (para migrations e pipeline);
- Para `fetch/backfill`, obtenha a **MAP_KEY** gratuita em
  https://firms.modaps.eosdis.nasa.gov/api/map_key/ e preencha `MAP_KEY=`;
- opcional: `VITE_*` públicas.

## 4. Banco de dados — dois caminhos SEM editar código

**A) Integração Vercel × Neon (recomendado, zero código):** o projeto já resolve
automaticamente `DATABASE_URL` / `DATABASE_URL_UNPOOLED` injetadas pela integração.
Migrations podem rodar via API admin (`POST /api/admin/migrate` — ver docs/VERCEL.md §3).

**B) Manual:** copie do painel Neon as duas URLs para `.env`:
- `DATABASE_URL=` (pooled; para a API) e `DATABASE_URL_DIRECT=` (direta; para migrations);
- Migrations a partir do local (também equivalente):
  ```bash
  cd backend
  alembic upgrade head           # usa DATABASE_URL_DIRECT (direta, NÃO pooled)
  alembic current                # confirma a revisão aplicada
  ```
  (ou, da raiz: `npm run db:migrate` / `npm run db:status`)

> O PostGIS precisa estar disponível no plano; a migration 0001 roda
> `CREATE EXTENSION IF NOT EXISTS postgis;` (no Neon/Supabase é suportado; se o plano
> reclamar, ative a extensão no painel do banco).


## 5. Rodar local

```bash
# Terminal 1: API
. .venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000
#   → http://localhost:8000/api/docs

# Terminal 2: SPA (proxy /api → :8000)
npm run dev --prefix frontend
#   → http://localhost:5173
```

## 6. Pipeline (local)

```bash
python -m pipeline --help
python -m pipeline status --sensor VIIRS_SNPP_SP     # data availability (requere MAP_KEY)
python -m pipeline seed-demo --rows 5000 --years 5   # DEMO (is_demo=true)
python -m pipeline clear-demo                        # remove DEMO
```

## 7. Deploy na Vercel

Ver `docs/VERCEL.md` (resumo: link, banco no Marketplace, secrets, migrations locais, primeiro deploy).

## 8. Agendar atualização diária (GitHub Actions)

- Ver `.github/workflows/pipeline.yml`; adicionar secrets no repo:
  `MAP_KEY`, `DATABASE_URL_DIRECT`. O workflow roda `fetch → ingest → aggregates → calendar` com idempotência.

## Solução de problemas

Ver `docs/TROUBLESHOOTING.md` (Python 3.14/wheels, PostGIS no Neon, cold start, MAP_KEY excedida).
