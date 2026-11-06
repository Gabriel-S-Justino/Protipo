# DATA_PIPELINE (fontes NASA: formatos reais validados)

## 5.1 FIRMS — validações feitas nesta fase

| Item | Resultado real-fonte |
|------|----------------------|
| Area API (base URL + template) | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}/{DATE}` |
| Chamada sem chave | HTTP 400, corpo `Invalid MAP_KEY.` — formatos reais do próprio recurso |
| Origem do MAP_KEY | `https://firms.modaps.eosdis.nasa.gov/api/map_key/` (conta Earthdata; limite: 5000 transações / 10 min) |
| max DAY_RANGE por chamada | **5 dias — validado com chave real** (`HTTP 400 "Invalid day range. Expects [1..5]"`); `MAX_DAY_RANGE=5` em `pipeline/firms.py` |
| `map_key_status` | **NÃO existe como API pública** → HTTP 400 `Invalid API call.` (o "Check status" é ação da página web); o status útil é via `data_availability` |
| data availability endpoint (`/api/data_availability/csv/{MAP_KEY}/{SOURCE}`) | ✔ HTTP 200, CSV `data_id,min_date,max_date` — ver tabela abaixo |
| Archive Download | usar para backfill histórico em massa (por país/região/ano) — validar URLs reais no momento do backfill |

Cobertura real obtida em 2026-11-05 (data_availability):

| SOURCE | min_date | max_date |
|--------|----------|----------|
| MODIS_SP | 2000-11-01 | **2026-08-31** |
| VIIRS_SNPP_SP | 2012-01-20 | 2026-07-31 |
| VIIRS_NOAA20_SP | 2018-04-01 | 2026-07-31 |
| VIIRS_NOAA20_NRT | 2026-08-01 | 2026-11-05 |
| **VIIRS_NOAA21_SP** (EXISTS) | 2023-03-01 | 2026-07-31 |
| VIIRS_NOAA21_NRT | 2024-01-17 | simultâneo (hoje) |

⚠ Janela NRT é deslizante (~90 dias): SNPP NRT cobria 2026-08-01 → **2026-11-02** (encerrou
exatamente em 2/11/2026 como previsto); histórico completo via SP + Archive Download.
Fonte `VIIRS_NOAA21_SP` já adicionada nesses adaptadores (`pipeline/normalization.py`).

Comportamento real confirmado da Area API (com chave):

- Com `{DATE}`: consulta os `DAY_RANGE` dias ANTERIORES à data (✔ testado 2024-09-15, MODIS_SP).
- Sem `{DATE}`: últimos dias até hoje (✔ testado NRT).
- Resposta vazia/só-header = nenhuma detecção (não é erro) ✔.
- CSV VIIRS NRT real (NOAA-21 5 dias no Ceará): `...satellite,instrument,confidence,version,bright_ti5,frp,daynight`
  → confiança l/n/h ✔, frp ✔; normalizado **389/389**, 0 rejeitos.
- CSV MODIS SP real: coluna extra `type` + frp; `satellite` já vem como "Terra"/"Aqua" ✔;
  normalizado **114/114**, 0 rejeitos.
- Arquivos no cache: `data/raw/VIIRS_NOAA21_NRT_*.csv`, `data/raw/MODIS_NRT_*.csv` — prontos
  para `python -m pipeline ingest <arquivo> --source <SOURCE>` quando o banco estiver disponível.

## Fontes (SOURCE) mapeadas em `pipeline/normalization.py`

```
MODIS_SP, MODIS_NRT
VIIRS_SNPP_SP, VIIRS_SNPP_NRT
VIIRS_NOAA20_SP, VIIRS_NOAA20_NRT
VIIRS_NOAA21_NRT          # SP do NOAA-21 ainda a confirmar via data_availability
```

- **SP** (reprocessado) tem prioridade para o histórico; **NRT** completa o período recente.
- **Regra NRT → SP sem duplicar** (a implementar na fase de backfill):
  - ingest SP windows primeiro; para o período coberto por SP, NRT só entra onde semanas faltem;
  - idem key (satellite, acquired_at, lat, lon, daynight, confidence_raw) + `ON CONFLICT DO NOTHING`
    evitam duplicação, e a fonte da linha fica em `data_sources` + `ingestion_batches`.
- S-NPP VIIRS: FIRMS para de atualizar em **2/11/2026** (histórico persiste); fluxo migra para NOAA-20/NOAA-21.
- Terra (~10h30) é o único matinal; Aqua (~13h30) é análogo ao VIIRS em horário (tratado em §6.4 da harmonização).

## 5.2 GIBS — validações feitas (WMTS GetCapabilities, 2026-11-05)

- WMTS 4326: `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml` (sem chave, tamanho 5,3 MB).
  Camadas confirmadas nesta fase (nomes de `ows:Identifier`):
  - `BlueMarble_NextGeneration`, `BlueMarble_ShadedRelief`
  - `VIIRS_SNPP_CorrectedReflectance_TrueColor`, `VIIRS_NOAA20_CorrectedReflectance_TrueColor`
  - `MODIS_Terra_CorrectedReflectance_TrueColor` / `MODIS_Aqua_CorrectedReflectance_TrueColor`
- Projeções e tilesMatrix a confirmar caso a camada escolhida para os mapas mude; GIBS é apenas visual.

## Regras de uso (§ 5.4 do master prompt)

## Comandos científicos implementados (fases 4–6)

```bash
python -m pipeline backfill --source MODIS_SP --start 2000-11-01 --end 2026-08-31 --sleep 0.5
python -m pipeline backfill --source VIIRS_SNPP_SP --start 2012-01-01 --end 2026-07-31
python -m pipeline harmonize --region 1            # fator mediana em overlap ≥6 meses ⇒ medium
python -m pipeline calendar  --region 1            # P(≥1 foco) por mês civil (fracão de anos)
python -m pipeline anomalies --region 1            # z-score vs baseline do mesmo mês
```

- `backfill`: janelas de **5 dias** (limite real da Area API), cache por checksum, ingest
  idempotente — seguro de reexecutar; pausa `--sleep` de cortesia; erros por janela não abortam.
- Honestidade: com overlap escasso o `harmonize` grava flag `low_confidence`/`insufficient`
  e `calendar/anomalies` mantêm `confidence='low'`/`level='info'` com nota (nunca um
  número polido sem base).
- Regiões: `regions.bbox_*` (Ceará = extremos aprox. IBGE) como delimitação provisória
  até ingestar a malha oficial; `is_demo` separa regiões-DEMO.

- MAP_KEY/Banco em variáveis de ambiente/secrets apenas.
- Cache por checksum em `data/raw/` — nunca re-baixar (economia de transações).
- Retry com backoff (3 tentativas); log de cada chamada **sem** a chave.
- Registro de proveniência (URL sem a chave, data/hora, versão, checksum) em `ingestion_batches`.
- Citar NASA/FIRMS/GIBS na interface (Metodologia) e nos créditos dos mapas.

## Arquivos CSV FIRMS (esquema, como validado na normalização)

- MODIS C6.1: `latitude, longitude, brightness, scan, track, acq_date, acq_time,
  satellite, confidence (0–100/x), version, bright_t31, daynight`
- VIIRS 375m: `latitude, longitude, bright_ti4, bright_ti5, scan, track, acq_date,
  acq_time, satellite, conf (l/n/h), version, daynight`
- **Não presumimos** a ordem/presença das colunas: identificar por cabeçalho com sinônimos (`COLUMN_SYNONYMS`).
- Respostas vazias da Area API = ausência de detecções (não é erro!).
