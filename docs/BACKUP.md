# BACKUP E RECUPERAÇÃO (sem Docker)

## Backup gerenciado (preferencial)

- **Neon**: point-in-time restore e **branches** por plano (produção separada por branch);
  verificar limites do plano em uso.
- **Supabase**: backups diários/semanais por plano + PitR.

## Backup manual com pg_dump (via CLI, sem Docker)

```bash
# Dump lógico (formato custom recomendado)
pg_dump "$DATABASE_URL_DIRECT" --format=custom --file backup_fip_$(date +%F).dump

# Verificar integridade do dump
pg_restore "$DATABASE_URL_DIRECT" --list --file=checklist.dump backup_fip_YYYY-MM-DD.dump

# Restaurar (EXIGE confirmação explícita antes de sobrescrever!)
# ⚠ Nunca restaurar em produção sem dupla confirmação do operador.
pg_restore "$DATABASE_URL_DIRECT" --clean --if-exists backup_fip_YYYY-MM-DD.dump
```

## Reconstrução completa a partir das fontes NASA (reprodutibilidade)

Como todos os dados derivados são reprodutíveis, é possível reconstruir TUDO:

```bash
python -m pipeline backfill      # baixa originais MODIS/VIIRS (archive + Area API)
python -m pipeline ingest ...    # ingere com idempotência
python -m pipeline harmonize     # gera harmonized_series (fase 4)
python -m pipeline calendar      # gera calendar_probabilities (fase 5)
python -m pipeline anomalies     # gera anomaly_results (fase 5)
```

`data_sources`/`ingestion_batches` registram proveniência e checksums para auditar.
