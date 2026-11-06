# Preparação nacional
Veja o passo a passo atualizado no README da raiz.

Requer Node 22+, Python compatível com os requirements e PostgreSQL 15+ com PostGIS.
API usa URL pooled; pipeline e Alembic usam URL direta.
URLs PostgreSQL comuns são normalizadas para o driver psycopg 3.

Antes de executar a carga:
1. Instale dependências de backend, pipeline e frontend.
2. Preencha DATABASE_URL, DATABASE_URL_DIRECT e MAP_KEY no .env.
3. Rode alembic -c backend/alembic.ini upgrade head.
4. Rode python -m pipeline boundaries para importar Brasil/27 UFs.
5. Consulte disponibilidade FIRMS por fonte e faça backfill das janelas reais.
6. Rode harmonize, calendar e anomalies.

O schema 0004 preserva proveniência SP/NRT em índices separados por fonte.
Seu downgrade automático é bloqueado para não colapsar esses originais.
CSV sem sidecar não fornece cobertura confiável para o calendário.
Não aproveite uma antiga carga do Ceará como histórico nacional.

Sem chave/banco não é possível gerar estatísticas nacionais reais.
A interface funciona e informa ausência/erro de dados sem fabricar probabilidades.
