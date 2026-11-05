# Arquitetura (sem Docker, Vercel-first)

Princípio central: **a Vercel serve e consulta; o pipeline calcula.**
Cálculo pesado (ingestão em massa, harmonização, calendário) roda fora da Vercel
(local + GitHub Actions agendado) e grava resultados pré-calculados no banco.
A API apenas lê esses resultados.

```
[NASA FIRMS / GIBS]
        │ download (MAP_KEY em secrets; cache por checksum)
        ▼
[Pipeline Python]  ← CLI local + GitHub Actions agendado (atualização diária)
        │ grava (conexão DIRETA)
        ▼
[PostgreSQL 16 + PostGIS gerenciado]  ← Neon via Vercel Marketplace (alternativa: Supabase)
        ▲ lê (conexão POOLED)
        │
[API FastAPI — Vercel Functions (Python), entrypoint api/index.py]
        ▲ /api/*
[SPA React + Vite — Vercel estático (frontend/dist)]
```

## Diretórios

| Camada    | Onde            | Notas |
|-----------|-----------------|-------|
| SPA       | `frontend/`     | React+TS+Vite+Tailwind; build em `frontend/dist` |
| API       | `backend/app` + `api/index.py` | FastAPI; bundle enxuto (sem libs pesadas) |
| Pipeline  | `pipeline/`     | virtualenv Python; nunca vai para a Vercel |
| Banco     | `backend/migrations` + `backend/alembic.ini` | Alembic; conexão direta |
| Dados     | `data/`         | fora do Git (exceto limites pequenos/amostras) |

## Decisões tomadas (e justificativas)

- **Unidade de harmonização**: célula × período (NUNCA correspondência pixel a pixel como equivalente).
- **Backend**: `backend/app` é importável (`uvicorn backend.app.main:app`) e referenciado por `api/index.py` na Vercel; o entrypoint ajusta o `sys.path` para a raiz do monorepo.
- **Conexões**: pooling externo (Neon pooler) + `NullPool` no engine da function (evita conexões órfãs em serverless); migrations/pipeline usam conexão direta.
- **Orçamento de armazenamento**: arquivos brutos grandes ficam fora do banco e do Git; no banco ficam detecções da região, agregados e tabelas derivadas. Medir o volume real antes de decidir particionamento.
- **Terra (manhã)** fora da série principal por padrão (`use_terra: false`): não existe passagem VIIRS matinal — ver `docs/HARMONIZATION.md`.
- **Nunca inventar dados**: consultas da API parametrizadas; endpoints respondem 503 com causa clara quando banco/pipeline não estão prontos; placeholders de fases futuras são honestos na UI.

## Riscos atuais

1. **Vercel Python runtime**: confirmar empacotamento atual (entrypoint/ASGI) e instalação de `api/requirements.txt` no primeiro deploy — detalhes mudam rápido; ver `docs/VERCEL.md`.
2. **Python 3.14 vs wheels**: pipeline exige wheels cp314 (resolvido com pandas 3.1.1, numpy 2.5.4 etc.; ver `pipeline/requirements.txt`).
3. **MAP_KEY**: limite de transações diárias — backfill em massa deve usar o **Archive Download** da FIRMS (arquivos anuais por país) e não a Area API.
4. **S-NPP**: fim da atualização operacional da FIRMS em 2/nov/2026; fluxo diário migra para NOAA-20/NOAA-21.

## Plano incremental (fases)

1. ✔ Base do projeto (monorepo, SPA, FastAPI mínima, configs Vercel, health).
2. ✔ Modelagem do banco (Alembic `0001_initial`: PostGIS + tabelas) + seeds DEMO.
3. ▶ Pipeline: ingestão idempotente, backfill (requere MAP_KEY), GitHub Actions.
4. Harmonização MODIS→VIIRS (calibração + validação cruzada por ano).
5. Calendário de probabilidade + anomalias (backtesting).
6. Interface completa: 3 mapas + todas as páginas.
7. Qualidade/produção: segurança, performance, backup, deploy final.
