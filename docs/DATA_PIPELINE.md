# DATA_PIPELINE (fontes NASA: formatos reais validados)

## 5.1 FIRMS — validações feitas nesta fase

| Item | Resultado real-fonte |
|------|----------------------|
| Area API (base URL + template) | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}/{DATE}` |
| Chamada sem chave | HTTP 400, corpo `Invalid MAP_KEY.` — formatos reais do próprio recurso |
| Origem do MAP_KEY | `https://firms.modaps.eosdis.nasa.gov/api/map_key/` (conta Earthdata) |
| max DAY_RANGE por chamada | **a confirmar com chave real** (suposta 10; implementado em `pipeline/firms.py#MAX_DAY_RANGE` com `min(day_range, MAX_DAY_RANGE)`) |
| data availability endpoint | `/api/data_availability/csv/{MAP_KEY}/{SENSOR}` — validar com chave |
| Archive Download | usar para backfill histórico em massa (por país/região/ano) — validar URLs reais no momento do backfill |

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
