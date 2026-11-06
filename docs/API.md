# API nacional
Base: /api. Swagger: /api/docs.

- GET /regions: Brasil e 27 UFs com limites importados e bbox.
- GET /regions/{id}/summary: atividade equivalente e série mensal.
- GET /dashboard/summary?region_id=: totais da grade unificada.
- GET /metadata/coverage: dias de aquisição nacional e parcela convertida.
- GET /series/unified?region_id=&period_type=month|week|day: uma série na escala VIIRS.
- GET /map/heat?region_id=&from=YYYY-MM-DD&to=YYYY-MM-DD: GeoJSON de atividade.
  Fim exclusivo. Grade fixa de 0,5°, uma propriedade weight; sem comparação de sensores.
- GET /calendar/probability?region_id=&period_type=week|month:
  calendário das 20 áreas com maior atividade esperada.
- GET /calendar/locations?region_id=&period_type=week|month&period=:
  GeoJSON de todas as áreas estimadas no período; probabilidade, IC, anos e validação.
- GET /tiles/grid_points/{z}/{x}/{y}.mvt: variante MVT do histórico unificado.
- GET /analytics/anomalies: análise exploratória da série equivalente com baseline anterior.
- Originais auditáveis: /detections, /metadata/sources e /ingestion/batches.
- POST /admin/migrate: protegido, aplica até 0004_brazil_science.

region_id ausente seleciona Brasil. Limites não importados: 503 com instrução.
Parâmetros e datas inválidos: 422/400. Sem resultados: coleção vazia; nunca dados falsos.
Consultas parametrizadas, timeout transacional compatível com pooler.
