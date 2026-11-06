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


## Banco conectado e consultas indisponíveis depois do deploy
Consulte /api/health. O resultado agora separa conexão, versão do schema,
limites IBGE, cobertura, harmonização e calendário. Database up não significa
que o ambiente nacional esteja preparado. Não crie outro banco só por esse aviso.

Se readiness=migration_pending, aplique 0004_brazil_science no banco existente.
O workflow manual Preparar banco nacional em GitHub Actions faz as migrações e
a importação IBGE usando o secret DATABASE_URL_DIRECT. Ele não roda em cada push.
Alternativa: POST /api/admin/migrate com a administração habilitada e o token já
configurado, depois python -m pipeline boundaries fora da Vercel.

Depois, carregue os CSVs nacionais com metadados e rode harmonize/calendar.
Preparar o schema não cria histórico nem probabilidades. O calendário exige pelo
menos três anos com períodos completos. Não exponha URLs de conexão ou tokens no chat.


## Falha de conexão com a API do IBGE no GitHub Actions
O comando boundaries importa a cópia oficial versionada em pipeline/assets,
sem chamar a API do IBGE durante a execução. A cópia inclui as 27 UFs, com
proveniência e checksum SHA-256; o Brasil é a união dessas mesmas geometrias.
São verificadas integridade, presença de todas as UFs, coordenadas e geometrias
PostGIS antes de confirmar a transação.

Após atualizar o código, abra Actions → Preparar banco nacional → Run workflow,
selecionando main. Re-run jobs de uma execução antiga usa o commit antigo e
pode repetir o timeout. A migração já aplicada é preservada por Alembic.


## Histórico insuficiente após pipeline update
update coleta apenas dois dias recentes. O calendário retorna
status=insufficient_data quando não há três anos com períodos completos; isso
é uma pendência de dados e não encerra a atualização diária com erro.

No GitHub Actions, execute Carga histórica nacional na main:
- source: ambos (VIIRS_NOAA20_SP e MODIS_SP);
- start_date: 2023-01-01;
- end_date: 2025-12-31;
- max_windows: 30 por fonte para limitar cada execução.

Repita a execução com os mesmos parâmetros enquanto windows_remaining for maior
que zero. O checkpoint fica em acquisition_coverage no banco, inclusive para
janelas sem focos. As janelas já confirmadas são puladas antes de baixar arquivos.
Não é necessário mudar o início manualmente. Esse intervalo inicial serve como
base mínima; a semana ISO 53 pode continuar sem amostra suficiente.

A carga brasileira pode conter milhões de registros e consumir armazenamento e
computação do banco. Monitore os limites do seu plano e ajuste max_windows.
Um workflow concluído com status in_progress significa que a parcela solicitada
terminou; não significa que o histórico inteiro ou o calendário estejam prontos.
Falhas reais de rede, disponibilidade ou ingestão continuam retornando erro.

O calendário só publica períodos com pelo menos três anos completos por área.
A harmonização MODIS exige também calibração validada no período compartilhado.
