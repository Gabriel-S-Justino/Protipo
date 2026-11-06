# Harmonização nacional MODIS → VIIRS

Implementação: `pipeline/science.py` e `pipeline/analytics.py`.

- Recorte dos originais pelo polígono nacional do IBGE, nunca apenas bbox.
- Grade analítica de 0,5°. Unidade: subcélulas ocupadas de 0,01° × dia UTC × dia/noite.
  Graus não são área constante; isso não equivale a pixels VIIRS de 375 m.
- Uma fonte VIIRS por dia coberto: S-NPP SP/NRT, depois NOAA-20 SP/NRT e NOAA-21 SP/NRT.
  A ordem é fixa; SP tem prioridade sobre NRT do mesmo satélite.
- Preserva registros de fontes diferentes (SP/NRT), mas não os soma no produto.
- Aqua MODIS apenas; Terra tem horário sem referência VIIRS equivalente.
- Calibração por área: mediana das razões em meses inteiros de cobertura compartilhada.
  Meses VIIRS zero são incluídos. MODIS zero não identifica uma razão multiplicativa.
- Mínimo de seis meses e três anos de calibração.
- Bootstrap por ano (300 reamostragens determinísticas); validação retirando um ano
  inteiro e comparando MAE com a transformação neutra.
- Sem calibração, fator não positivo ou MAE pior que a referência: exclui MODIS.
  Nunca presume fator 1 para preencher uma lacuna.
- VIIRS coberto com zero detecções continua zero, sem substituição por MODIS.
- O histórico anterior a Aqua e as áreas não calibradas podem ficar sem série convertida.

Limitações: mudança de plataforma VIIRS, nuvens, frequência de revisita, grade angular
e relação multiplicativa podem afetar a continuidade. A validação não transforma
a série em previsão confiável de ignição. Não existe garantia de acurácia futura.
O pipeline processa uma área por vez com cursores de banco; originais ficam intactos.
