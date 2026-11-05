# DATABASE (modelagem e operações)

Fonte da verdade do DDL: `backend/migrations/versions/0001_initial.py` (Alembic).

## Tabelas

| Tabela                 | Papel |
|------------------------|-------|
| `data_sources`         | catálogo MODIS/VIIRS (SP/NRT) + DEMO_SYNTHETIC |
| `ingestion_batches`    | relatório por lote (checksum, totais, status, versão) |
| `pipeline_runs`        | execução de cada comando do pipeline |
| `fire_detections`      | **originais preservados** + `geometry(Point,4326)` + idem-key única |
| `regions`              | estado/município IBGE/regiões custom (hierarquia via parent_id) |
| `spatial_cells`        | grades multi-resolução (viirs375m, modis1km, h3_10km...) |
| `cell_period_aggregates` | contagens/FRP/distribuição de confiança por célula × período |
| `harmonization_models` | método, parâmetros, calibração, métricas (versionado) |
| `harmonized_series`    | série unificada (raw, viirs-eq, IC 95%, qualidade) |
| `calendar_probabilities` | P(≥1 foco) por período do ano com IC e confiança |
| `anomaly_results`      | períodos/regiões atípicas + metodologia |

## Decisões-chave

- **Geometry vs Geography**: `geometry(Point,4326)` + GiST para armazenar/consultar;
  para distâncias/áreas usar `geography` ou SIRGAS 2000/UTM 24S (Ceará ~ zone 24S).
- **Idem key** de `fire_detections`: (satellite, acquired_at, lat, lon, daynight, confidence_raw)
  com índice único → deduplicação garantida pelo banco + `ON CONFLICT DO NOTHING`.
- **is_demo**: separa DEMO de real; consultas públicas excluem `is_demo=TRUE`.
- **Particionamento**: modelar com `date`, apenas ativar (partição por ano) após medir volume real.
- **Índices principais**: idem-key, (acquired_at, instrument), GiST em geom,
  lookups das tabelas derivadas (harmonized_series/calendar/cell_period_aggregates).

## Operações

- Migrations: `cd backend && DATABASE_URL_DIRECT=... alembic upgrade head` (local/CI).
- Seeds DEMO: `python -m pipeline seed-demo|clear-demo`.
- Backups: ver docs/BACKUP.md (pg_dump manual + recursos do provedor).
