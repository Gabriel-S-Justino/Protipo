# Pipeline nacional

Consulte `README.md` para a sequência de execução. Comandos:
`boundaries`, `status`, `fetch`, `ingest`, `backfill`, `harmonize`,
`calendar`, `anomalies`, `update`, `report`, `validate`.

- Bbox de coleta nacional: oeste -74, sul -34, leste -28, norte 6.
- Recorte analítico posterior pelos polígonos oficiais do IBGE.
- FIRMS Area API: janelas de 1–5 dias; DATE é o início da janela.
  Referência: https://firms.modaps.eosdis.nasa.gov/api/area
- Backfill inclui os dois extremos e ajusta o tamanho da última janela.
- Datas recentes têm cache revalidado; a chave do cache contém datas concretas.
- Resposta vazia válida é preservada; disponibilidade da fonte deve cobrir todo o intervalo.
- Metadados JSON acompanham CSV: bbox, datas, fonte, checksum e disponibilidade.
- Ingestão registra cobertura inclusive sem detecções; rejeições impedem registrar cobertura.
- Registros originais SP/NRT ficam separados por fonte; produto escolhe uma fonte.
- CSVs antigos sem metadados não comprovam cobertura nacional de dias negativos.
- `update` coleta duas datas UTC completas para NOAA20, NOAA21 e MODIS;
  ingere cada arquivo com a fonte correta, harmoniza, calcula calendário e anomalias.
- Falhas não são mascaradas por `|| true`. Uma janela com erro interrompe publicação diária.
- Grandes históricos exigem tempo e respeito aos limites FIRMS; ajuste `--sleep`.
  Importação Archive Download com cobertura auditada é uma evolução futura.
- Transições entre plataformas ainda exigem avaliação científica adicional.

Limites e fontes são externos: consulte `status` antes de escolher intervalos.
Credenciais nunca são gravadas nos arquivos ou logs.
