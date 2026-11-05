"""Fire Intelligence Pipeline — processamento científico FORA da Vercel.

Comandos (python -m pipeline <comando>):
    fetch        Baixa CSVs da FIRMS (Area API / archive) com cache por checksum
    ingest       Ingestão idempotente de arquivo(s) local(is) no banco
    backfill     Série histórica completa (janelas paginadas / archive)
    validate     Valida formato/esquema dos arquivos baixados
    harmonize    (fase 4) Calibra MODIS→VIIRS e grava harmonized_series
    calendar     (fase 5) Calcula o calendário probabilístico
    anomalies    (fase 5) Detecta períodos/regiões atípicos
    report       Relatório da última ingestão/execução
    status       Verifica disponibilidade de sensores (data availability)
    seed-demo    Popula banco com dados sintéticos DEMO (is_demo=true)
    clear-demo   Remove os dados DEMO
"""
