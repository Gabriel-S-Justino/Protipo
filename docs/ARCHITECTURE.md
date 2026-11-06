# Arquitetura nacional
A API serve produtos; o pipeline calcula.
- frontend/: React/TypeScript/Vite, seleção Brasil/UF, MapLibre e calendário espacial.
- backend/app/: FastAPI com consultas parametrizadas na grade equivalente.
- backend/migrations/: PostGIS, originais e produtos derivados; head 0004_brazil_science.
- pipeline/: coleta auditada, limites IBGE, harmonização, calendário e anomalias.
- .github/workflows/pipeline.yml: atualização diária fora da Vercel.
- api/index.py: entrada ASGI da Vercel.
- data/: dados de trabalho e metadados fora do Git.

Dados: FIRMS → originais por fonte + cobertura → grade harmonizada → API.
Migrations não inicializam limites ou dados: execute boundaries e a carga nacional.
Não existe restrição ao Ceará nem visualização comparativa dos sensores no produto.
