# TROUBLESHOOTING

## Python 3.14: "fatal error: Python.h" ao instalar pandas/etc

As versões antigas (pandas 2.x) não têm wheel para cp314 → pip tenta compilar
e falta o header. Solução: usar as versões com wheel cp314 fixadas em
`pipeline/requirements.txt` (pandas 3.1.1, numpy 2.5.4, ...). Alternativa:
instalar `python3.14-dev` via gerenciador de pacotes.

## Starlette TestClient: "requires the httpx2 package"

Starlette atual pergunta por `httpx2` (fork compatível). Já incluso nas
preferências de teste (`httpx2==2.16.0`).

## MAP_KEY

- `"Invalid MAP_KEY."` com HTTP 400 → chave ausente/inválida; ver docs/SETUP.md §3.
- Limite de transações: conferir status da chave (`python -m pipeline status --sensor ...`).
- Nunca commitar a chave; secrets do repo (CI) e `.env` local.

## PostGIS no Neon/Supabase

- `CREATE EXTENSION postgis` pode exigir ativação no painel/ACL do plano.
- Migrations usam `DATABASE_URL_DIRECT` (não a pooled/pooler).

## Cold start / function lenta

- Endpoints com `statement_timeout` (5s default) evitam travar a function;
  ver docs/VERCEL.md para memória/duração.

## vercel dev + SPA

- Se `vercel dev` não subir a API, rodar frontend e API separadamente:
  `npm run dev --prefix frontend` + `uvicorn backend.app.main:app --port 8000`.
