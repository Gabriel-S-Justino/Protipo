# Malhas oficiais IBGE

br_ufs.geojson é a resposta oficial da API de malhas v3 para Brasil, intrarregião
UF, qualidade minima. Foi obtida do próprio IBGE em 2026-11-06. Não é dado sintético.

br_ufs.provenance.json registra URL, instante da coleta e SHA-256 dos bytes originais.
A coleta não indica o ano de referência territorial. As geometrias são simplificadas,
adequadas ao recorte da grade analítica de 0,5°; não servem para delimitação cadastral.

A cópia pequena (cerca de 100 kB) é versionada para tornar a preparação reprodutível
sem depender da disponibilidade da API pública. Não contém detecções NASA nem segredos.
O comando boundaries valida os 27 códigos, coordenadas e checksum antes de acessar
o banco; todas as alterações são confirmadas em uma única transação.

Para atualizar, obtenha novamente a URL registrada, revise as 27 UFs, atualize o
checksum/proveniência e rode pipeline/tests/test_geography.py antes de publicar.
Créditos e documentação: https://servicodados.ibge.gov.br/api/docs/malhas?versao=3
