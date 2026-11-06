# Calendário espacial semanal e mensal

`python -m pipeline calendar` lê a série unificada da grade nacional.
Publica até 53 semanas ISO e 12 meses por área, com localização consultável no mapa.

## Denominador e cobertura
Cobertura vem de `acquisition_coverage`, registrada somente após consulta FIRMS
nacional válida e ingestão sem linhas rejeitadas. O download verifica a disponibilidade
da fonte, o período e o checksum; respostas vazias válidas também registram cobertura.
Cobertura indica aquisição/ingestão bem-sucedida, não ausência de nuvens.

Um período só entra se todos os seus dias foram adquiridos e o período já terminou.
Sem cobertura, não se infere zero. Com cobertura, dias sem atividade são negativos.
Usa os dias VIIRS e, nas áreas calibradas, dias MODIS convertidos quando VIIRS está ausente.
Exige pelo menos três anos completos por bucket. Semana 53 usa o ano ISO correto.

## Estimativa e validação
P = fração de anos cobertos com atividade equivalente >=1.
O intervalo de Wilson de 95% expressa a incerteza amostral da frequência.
Não engloba completamente a incerteza da harmonização/sensores.
A contagem esperada é a média da atividade equivalente nos mesmos períodos cobertos.

Brier rolling-origin: cada ano é avaliado com os anteriores, após três anos de treino.
Sem anos de teste, Brier é nulo. Confiança continua baixa se a base for curta.
Não é um modelo meteorológico, nem uma probabilidade validada de incêndio futuro.

## Interface
Seleção nacional/estadual, semana/mês e ano de planejamento. O ano apenas organiza
as datas, sem extrapolar tendência. Mostra mapa, ranking, intervalo, anos usados e
tabela das 20 áreas de maior atividade média. Todas as áreas estimadas aparecem no
mapa do período. Sem estimativa aparece como indisponível, nunca como risco zero.

A grade é de 0,5° (~50 km); seleções estaduais usam o ponto representativo da célula.
Áreas na divisa podem incluir atividade de mais de um estado.
